"""Repositorio de las vistas transversales del usuario (única capa que toca la BD)."""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import Row, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, ProjectMembership, Workspace, WorkspaceMembership
from app.models.enums import WorkspaceRole


class MeRepository:
    """Consultas acotadas al usuario autenticado."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_accessible_projects(self, user_id: UUID) -> Sequence[Row[Any]]:
        """Proyectos accesibles por el usuario en TODOS sus workspaces (sin N+1).

        Unión (vía JOIN/condición WHERE):
        - projects de workspaces donde el usuario es owner/admin (acceso implícito a todos), y
        - projects donde tiene membresía de proyecto explícita (member/guest).

        Devuelve, por proyecto: datos del project, ``workspace_name`` (join) y los roles del
        usuario (workspace y proyecto) para calcular el rol efectivo en el servicio.
        """
        stmt = (
            select(
                Project.project_id,
                Project.name,
                Project.workspace_id,
                Project.created_at,
                Workspace.name.label("workspace_name"),
                WorkspaceMembership.role.label("workspace_role"),
                ProjectMembership.role.label("project_role"),
            )
            .join(Workspace, Workspace.workspace_id == Project.workspace_id)
            .join(
                WorkspaceMembership,
                (WorkspaceMembership.workspace_id == Project.workspace_id)
                & (WorkspaceMembership.user_id == user_id),
            )
            .outerjoin(
                ProjectMembership,
                (ProjectMembership.project_id == Project.project_id)
                & (ProjectMembership.user_id == user_id),
            )
            .where(
                or_(
                    WorkspaceMembership.role.in_([WorkspaceRole.OWNER, WorkspaceRole.ADMIN]),
                    ProjectMembership.user_id.is_not(None),
                )
            )
            .order_by(Workspace.name, Project.created_at)
        )
        return (await self._session.execute(stmt)).all()
