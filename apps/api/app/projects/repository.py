"""Repositorio de projects y sus membresías (sobre ``WorkspaceScopedRepository``).

Todas las lecturas de projects parten de ``scoped_select()``, que impone el filtro por
``workspace_id`` del contexto (aislamiento). Las membresías de proyecto se acotan al proyecto.
"""

from collections.abc import Sequence
from uuid import UUID, uuid4

from sqlalchemy import Row, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import WorkspaceScopedRepository
from app.models import Project, ProjectMembership, User, WorkspaceMembership
from app.models.enums import ProjectRole, WorkspaceRole


class ProjectRepository(WorkspaceScopedRepository):
    """Acceso a datos de ``projects`` y ``project_memberships`` dentro de un workspace."""

    model = Project

    def __init__(self, session: AsyncSession, workspace_id: UUID) -> None:
        super().__init__(session, workspace_id)

    async def flush(self) -> None:
        await self._session.flush()

    # ── Projects ──
    def add(self, *, name: str, classification: str | None) -> Project:
        project = Project(
            project_id=uuid4(),
            workspace_id=self._workspace_id,
            name=name,
            classification=classification,
        )
        self._session.add(project)
        return project

    async def get(self, project_id: UUID) -> Project | None:
        stmt = self.scoped_select().where(Project.project_id == project_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_all(self) -> Sequence[Project]:
        return (
            (await self._session.execute(self.scoped_select().order_by(Project.created_at)))
            .scalars()
            .all()
        )

    async def list_for_member(self, user_id: UUID) -> Sequence[Project]:
        """Projects del workspace donde el usuario tiene membresía de proyecto explícita."""
        stmt = (
            self.scoped_select()
            .join(ProjectMembership, ProjectMembership.project_id == Project.project_id)
            .where(ProjectMembership.user_id == user_id)
            .order_by(Project.created_at)
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def delete(self, project: Project) -> None:
        await self._session.delete(project)

    # ── Usuarios / rol de workspace (para alta de miembros) ──
    async def get_user_by_email(self, email: str) -> User | None:
        return (
            await self._session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()

    async def get_workspace_role(self, user_id: UUID) -> WorkspaceRole | None:
        """Rol de workspace del usuario en ESTE workspace (None si no es miembro)."""
        stmt = select(WorkspaceMembership.role).where(
            WorkspaceMembership.workspace_id == self._workspace_id,
            WorkspaceMembership.user_id == user_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    # ── Membresías de proyecto ──
    async def get_membership(self, project_id: UUID, user_id: UUID) -> ProjectMembership | None:
        stmt = select(ProjectMembership).where(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == user_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    def add_membership(
        self, *, project_id: UUID, user_id: UUID, role: ProjectRole
    ) -> ProjectMembership:
        membership = ProjectMembership(
            project_membership_id=uuid4(),
            user_id=user_id,
            project_id=project_id,
            role=role,
        )
        self._session.add(membership)
        return membership

    async def delete_membership(self, membership: ProjectMembership) -> None:
        await self._session.delete(membership)

    async def list_members(self, project_id: UUID) -> Sequence[Row[tuple[User, ProjectMembership]]]:
        stmt = (
            select(User, ProjectMembership)
            .join(ProjectMembership, ProjectMembership.user_id == User.user_id)
            .where(ProjectMembership.project_id == project_id)
            .order_by(User.email)
        )
        return (await self._session.execute(stmt)).all()
