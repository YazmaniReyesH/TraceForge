"""Servicio de projects: CRUD + membresías de proyecto (no conoce HTTP)."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Row
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constraints import PROJECT_MEMBERSHIP_UNIQUE
from app.core.integrity import translate_integrity_error
from app.core.security import WorkspaceContext
from app.models import Project, ProjectMembership, User
from app.models.enums import ProjectRole, WorkspaceRole
from app.projects.errors import (
    GuestMustBeViewerError,
    NotWorkspaceMemberError,
    ProjectMemberExistsError,
    UserNotFoundError,
)
from app.projects.repository import ProjectRepository
from app.projects.schemas import ProjectUpdate


class ProjectService:
    """Reglas de negocio de projects y de sus membresías."""

    def __init__(self, repository: ProjectRepository, session: AsyncSession) -> None:
        self._repo = repository
        self._session = session

    # ── CRUD de projects ──
    async def create(self, *, name: str, classification: str | None) -> Project:
        project = self._repo.add(name=name, classification=classification)
        await self._session.commit()
        return project

    async def list_visible(self, context: WorkspaceContext) -> Sequence[Project]:
        """owner/admin ven todos los projects del workspace; member/guest solo los suyos."""
        if context.workspace_role in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
            return await self._repo.list_all()
        return await self._repo.list_for_member(context.user.user_id)

    async def get(self, project_id: UUID) -> Project | None:
        return await self._repo.get(project_id)

    async def update(self, project_id: UUID, data: ProjectUpdate) -> Project | None:
        project = await self._repo.get(project_id)
        if project is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        await self._session.commit()
        return project

    async def delete(self, project_id: UUID) -> bool:
        project = await self._repo.get(project_id)
        if project is None:
            return False
        await self._repo.delete(project)
        await self._session.commit()
        return True

    # ── Membresías de proyecto ──
    async def list_members(self, project_id: UUID) -> Sequence[Row[tuple[User, ProjectMembership]]]:
        return await self._repo.list_members(project_id)

    async def add_member(
        self, *, project_id: UUID, email: str, role: ProjectRole
    ) -> tuple[User, ProjectMembership]:
        """Alta de miembro de proyecto (usuario existente). Aplica la regla guest=viewer."""
        user = await self._repo.get_user_by_email(email.strip().lower())
        if user is None:
            raise UserNotFoundError
        self._assert_role_allowed(await self._repo.get_workspace_role(user.user_id), role)
        if await self._repo.get_membership(project_id, user.user_id) is not None:
            raise ProjectMemberExistsError
        membership = self._repo.add_membership(
            project_id=project_id, user_id=user.user_id, role=role
        )
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            mapped = translate_integrity_error(
                exc, {PROJECT_MEMBERSHIP_UNIQUE: ProjectMemberExistsError}
            )
            if mapped is exc:
                raise
            raise mapped from exc
        return user, membership

    async def change_member_role(
        self, *, project_id: UUID, user_id: UUID, role: ProjectRole
    ) -> ProjectMembership | None:
        membership = await self._repo.get_membership(project_id, user_id)
        if membership is None:
            return None
        self._assert_role_allowed(await self._repo.get_workspace_role(user_id), role)
        membership.role = role
        await self._session.commit()
        return membership

    async def remove_member(self, *, project_id: UUID, user_id: UUID) -> bool:
        membership = await self._repo.get_membership(project_id, user_id)
        if membership is None:
            return False
        await self._repo.delete_membership(membership)
        await self._session.commit()
        return True

    @staticmethod
    def _assert_role_allowed(workspace_role: WorkspaceRole | None, role: ProjectRole) -> None:
        """Valida que el usuario sea miembro del workspace y respeta guest=viewer."""
        if workspace_role is None:
            raise NotWorkspaceMemberError
        if workspace_role == WorkspaceRole.GUEST and role != ProjectRole.VIEWER:
            raise GuestMustBeViewerError
