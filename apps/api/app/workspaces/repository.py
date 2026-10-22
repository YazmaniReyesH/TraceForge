"""Repositorio de workspaces y sus membresías (única capa que toca la BD)."""

from collections.abc import Sequence
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Workspace, WorkspaceMembership
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
