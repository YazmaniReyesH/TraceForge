"""Autorización central de TraceForge (ADR-0002, ADR-0008).

Contiene:
- la **matriz de permisos** (rol de workspace x acción), fuente única;
- el **rol efectivo** de proyecto (función pura, piso implícito de owner/admin);
- el **contexto de autorización** por ruta (``get_workspace_context``) y
- la dependencia **``requiere_permiso``**.

Alcance por ruta: el ``workspace_id`` viaja en la URL; la autorización lo toma de la ruta,
verifica membresía y resuelve el rol. No hay "workspace activo" por header/sesión.

Nota de capas: la resolución de membresía es el **gate de autorización** (infraestructura
transversal), por eso su consulta vive aquí y no en un repository de dominio. El acceso a
datos de negocio sí pasa siempre por repositories.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.db import get_session
from app.models import User, WorkspaceMembership
from app.models.enums import ProjectRole, WorkspaceRole


class Permission(StrEnum):
    """Acciones autorizables. Se amplía en F0-T4b-2 (projects, memberships, …)."""

    WORKSPACES_READ = "workspaces:read"
    WORKSPACES_UPDATE = "workspaces:update"
    WORKSPACES_DELETE = "workspaces:delete"
    WORKSPACES_MANAGE_MEMBERS = "workspaces:manage_members"


# ── Matriz de permisos: rol de workspace -> acciones permitidas (fuente única) ──
# (ADR-0002) guest no tiene overview del workspace: sin permisos a nivel workspace.
PERMISSION_MATRIX: dict[WorkspaceRole, frozenset[Permission]] = {
    WorkspaceRole.OWNER: frozenset(Permission),
    WorkspaceRole.ADMIN: frozenset(
        {
            Permission.WORKSPACES_READ,
            Permission.WORKSPACES_UPDATE,
            Permission.WORKSPACES_MANAGE_MEMBERS,
        }
    ),
    WorkspaceRole.MEMBER: frozenset({Permission.WORKSPACES_READ}),
    WorkspaceRole.GUEST: frozenset(),
}


def has_permission(role: WorkspaceRole, action: Permission) -> bool:
    """True si el ``role`` de workspace puede ejecutar ``action`` según la matriz."""
    return action in PERMISSION_MATRIX.get(role, frozenset())


def effective_project_role(
    workspace_role: WorkspaceRole, project_role: ProjectRole | None
) -> ProjectRole | None:
    """Rol efectivo sobre un proyecto (ADR-0002, "Rol efectivo e invariantes").

    - owner/admin: acceso implícito a todos los proyectos como **piso** = ``lead``; la
      membresía de proyecto solo puede sumar, nunca restar (y no hay nada sobre ``lead``).
    - member/guest: el acceso proviene **solo** de la membresía explícita; sin ella,
      ``None`` (sin acceso).

    Nota: en F0-T4b-1 se usa a nivel workspace; el nivel proyecto se consumirá en F0-T4b-2,
    pero la función ya está completa y cubierta por pruebas.
    """
    if workspace_role in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
        return ProjectRole.LEAD
    return project_role


@dataclass(frozen=True)
class WorkspaceContext:
    """Contexto de autorización resuelto para una petición a un recurso de workspace."""

    user: User
    workspace_id: UUID
    workspace_role: WorkspaceRole


async def get_workspace_context(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkspaceContext:
    """Resuelve (user, workspace_id, rol) desde la ruta y la membresía.

    404 genérico si no hay membresía — exista o no el workspace — para **no filtrar la
    existencia** del workspace a quien no es miembro (criterio documentado en ADR-0008).
    """
    stmt = select(WorkspaceMembership).where(
        WorkspaceMembership.user_id == user.user_id,
        WorkspaceMembership.workspace_id == workspace_id,
    )
    membership = (await session.execute(stmt)).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace no encontrado")
    return WorkspaceContext(user=user, workspace_id=workspace_id, workspace_role=membership.role)


def requiere_permiso(
    action: Permission,
) -> Callable[[WorkspaceContext], Awaitable[WorkspaceContext]]:
    """Dependencia que exige ``action`` sobre el workspace de la ruta (403 si no autorizado).

    Todo endpoint protegido de recurso de workspace nace con esta dependencia.
    """

    async def checker(
        context: WorkspaceContext = Depends(get_workspace_context),
    ) -> WorkspaceContext:
        if not has_permission(context.workspace_role, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para esta acción",
            )
        return context

    return checker
