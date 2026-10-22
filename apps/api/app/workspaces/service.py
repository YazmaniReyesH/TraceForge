"""Servicio de workspaces: reglas de negocio y transacciones (no conoce HTTP).

Aquí viven los invariantes de owner (ADR-0002, "Rol efectivo e invariantes"): un workspace
siempre tiene **exactamente un owner**; no se puede degradar ni quitar al único owner; la única
forma de dejar de serlo es **transferir la propiedad** (operación atómica).
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Row
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constraints import WORKSPACE_MEMBERSHIP_UNIQUE
from app.core.integrity import translate_integrity_error
from app.models import User, Workspace, WorkspaceMembership
from app.models.enums import WorkspaceRole
from app.workspaces.errors import (
    AlreadyOwnerError,
    CannotAssignOwnerRoleError,
    CannotModifySoleOwnerError,
    MemberExistsError,
    NotWorkspaceMemberError,
    UserNotFoundError,
)
from app.workspaces.repository import WorkspaceRepository


class WorkspaceService:
    """Creación y lectura de workspaces."""

    def __init__(self, repository: WorkspaceRepository, session: AsyncSession) -> None:
        self._repo = repository
        self._session = session

    async def create(self, *, name: str, owner: User) -> Workspace:
        """Crea el workspace y, en la MISMA transacción, la membresía de ``owner``.

        Único invariante de esta tanda: crear workspace ⇒ owner. Los invariantes
        protectores de owner (al menos uno, transferencia atómica) son F0-T4b-2.
        """
        workspace = self._repo.add_workspace(name=name)
        # El workspace debe existir antes que la membresía (FK). Sin relationship ORM,
        # forzamos el orden con un flush explícito.
        await self._repo.flush()
        self._repo.add_membership(
            user_id=owner.user_id,
            workspace_id=workspace.workspace_id,
            role=WorkspaceRole.OWNER,
        )
        await self._session.commit()
        return workspace

    async def list_for_user(self, user_id: UUID) -> Sequence[Workspace]:
        """Lista los workspaces del usuario (aislamiento por membresía)."""
        return await self._repo.list_for_user(user_id)

    async def get(self, workspace_id: UUID) -> Workspace | None:
        """Devuelve el workspace por id. La membresía ya la verificó el contexto."""
        return await self._repo.get_by_id(workspace_id)

    # ── Gestión de miembros ──
    async def list_members(
        self, workspace_id: UUID
    ) -> Sequence[Row[tuple[User, WorkspaceMembership]]]:
        return await self._repo.list_members(workspace_id)

    async def add_member(
        self, *, workspace_id: UUID, email: str, role: WorkspaceRole
    ) -> tuple[User, WorkspaceMembership]:
        """Añade un usuario existente al workspace. ``owner`` no se asigna aquí (transferencia)."""
        if role == WorkspaceRole.OWNER:
            raise CannotAssignOwnerRoleError
        user = await self._repo.get_user_by_email(email.strip().lower())
        if user is None:
            raise UserNotFoundError
        if await self._repo.get_membership(workspace_id, user.user_id) is not None:
            raise MemberExistsError
        membership = self._repo.add_membership(
            user_id=user.user_id, workspace_id=workspace_id, role=role
        )
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            mapped = translate_integrity_error(
                exc, {WORKSPACE_MEMBERSHIP_UNIQUE: MemberExistsError}
            )
            if mapped is exc:
                raise
            raise mapped from exc
        return user, membership

    async def change_member_role(
        self, *, workspace_id: UUID, user_id: UUID, role: WorkspaceRole
    ) -> WorkspaceMembership:
        """Cambia el rol de un miembro. No se asigna ni se degrada al owner por esta vía."""
        if role == WorkspaceRole.OWNER:
            raise CannotAssignOwnerRoleError
        membership = await self._repo.get_membership(workspace_id, user_id)
        if membership is None:
            raise NotWorkspaceMemberError
        if membership.role == WorkspaceRole.OWNER:
            # Degradar al único owner rompe "al menos un owner": hay que transferir.
            raise CannotModifySoleOwnerError
        membership.role = role
        await self._session.commit()
        return membership

    async def remove_member(self, *, workspace_id: UUID, user_id: UUID) -> None:
        """Quita a un miembro (y sus membresías de proyecto en el workspace). No al owner."""
        membership = await self._repo.get_membership(workspace_id, user_id)
        if membership is None:
            raise NotWorkspaceMemberError
        if membership.role == WorkspaceRole.OWNER:
            raise CannotModifySoleOwnerError
        await self._repo.delete_project_memberships_for_user(workspace_id, user_id)
        await self._repo.delete_membership(membership)
        await self._session.commit()

    async def transfer_ownership(
        self, *, workspace_id: UUID, current_owner_id: UUID, new_owner_id: UUID
    ) -> None:
        """Transfiere la propiedad de forma ATÓMICA: nuevo -> owner, anterior -> admin.

        Se degrada primero al owner actual (libera el índice único parcial de owner) y luego se
        promueve al nuevo, todo en una transacción.
        """
        if new_owner_id == current_owner_id:
            raise AlreadyOwnerError
        new_membership = await self._repo.get_membership(workspace_id, new_owner_id)
        if new_membership is None:
            raise NotWorkspaceMemberError
        current_membership = await self._repo.get_membership(workspace_id, current_owner_id)
        if current_membership is None or current_membership.role != WorkspaceRole.OWNER:
            # Defensivo: el gate ya exige que el solicitante sea owner.
            raise CannotModifySoleOwnerError
        current_membership.role = WorkspaceRole.ADMIN
        await self._repo.flush()  # aplica la degradación antes de promover (índice parcial)
        new_membership.role = WorkspaceRole.OWNER
        await self._session.commit()
