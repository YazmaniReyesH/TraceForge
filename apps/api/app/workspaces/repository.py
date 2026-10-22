"""Repositorio de workspaces y sus membresías (única capa que toca la BD)."""

from collections.abc import Sequence
from uuid import UUID, uuid4

from sqlalchemy import Row, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, ProjectMembership, User, Workspace, WorkspaceMembership
from app.models.enums import WorkspaceRole


class WorkspaceRepository:
    """Acceso a datos de ``workspaces`` y ``workspace_memberships``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def flush(self) -> None:
        """Vuelca INSERTs pendientes SIN commit (p. ej. para respetar el orden de FKs)."""
        await self._session.flush()

    def add_workspace(self, *, name: str) -> Workspace:
        """Agrega un workspace (id generado en la app). No hace commit."""
        workspace = Workspace(workspace_id=uuid4(), name=name)
        self._session.add(workspace)
        return workspace

    def add_membership(
        self, *, user_id: UUID, workspace_id: UUID, role: WorkspaceRole
    ) -> WorkspaceMembership:
        """Agrega una membresía de workspace. No hace commit."""
        membership = WorkspaceMembership(
            workspace_membership_id=uuid4(),
            user_id=user_id,
            workspace_id=workspace_id,
            role=role,
        )
        self._session.add(membership)
        return membership

    async def get_by_id(self, workspace_id: UUID) -> Workspace | None:
        """Devuelve un workspace por id (sin verificar membresía)."""
        return await self._session.get(Workspace, workspace_id)

    async def list_for_user(self, user_id: UUID) -> Sequence[Workspace]:
        """Workspaces donde el usuario tiene membresía (aislamiento: solo los suyos)."""
        stmt = (
            select(Workspace)
            .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.workspace_id)
            .where(WorkspaceMembership.user_id == user_id)
            .order_by(Workspace.created_at)
        )
        return (await self._session.execute(stmt)).scalars().all()

    # ── Membresías de workspace ──
    async def get_user_by_email(self, email: str) -> User | None:
        return (
            await self._session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()

    async def get_membership(self, workspace_id: UUID, user_id: UUID) -> WorkspaceMembership | None:
        stmt = select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_members(
        self, workspace_id: UUID
    ) -> Sequence[Row[tuple[User, WorkspaceMembership]]]:
        stmt = (
            select(User, WorkspaceMembership)
            .join(WorkspaceMembership, WorkspaceMembership.user_id == User.user_id)
            .where(WorkspaceMembership.workspace_id == workspace_id)
            .order_by(User.email)
        )
        return (await self._session.execute(stmt)).all()

    async def delete_membership(self, membership: WorkspaceMembership) -> None:
        await self._session.delete(membership)

    async def delete_project_memberships_for_user(self, workspace_id: UUID, user_id: UUID) -> None:
        """Quita las membresías de proyecto del usuario DENTRO de este workspace."""
        project_ids = select(Project.project_id).where(Project.workspace_id == workspace_id)
        await self._session.execute(
            delete(ProjectMembership).where(
                ProjectMembership.user_id == user_id,
                ProjectMembership.project_id.in_(project_ids),
            )
        )
