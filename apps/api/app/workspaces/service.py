"""Servicio de workspaces: reglas de negocio y transacciones (no conoce HTTP)."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Workspace
from app.models.enums import WorkspaceRole
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
