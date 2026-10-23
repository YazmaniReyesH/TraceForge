"""Autorización central de TraceForge (ADR-0002, ADR-0008).

Contiene:
- la **matriz de permisos** de workspace (rol de workspace x acción) y la de **proyecto**
  (rol de proyecto x acción), fuente única;
- el **rol efectivo** de proyecto (función pura, piso implícito de owner/admin);
- los **contextos de autorización** por ruta (``get_workspace_context``,
  ``get_project_context``) y las dependencias **``requiere_permiso``** /
  **``requiere_permiso_proyecto``**.

Alcance por ruta: el ``workspace_id`` (y el ``project_id``) viajan en la URL; la autorización
los toma de la ruta, verifica membresía y resuelve el rol. No hay "workspace activo" por header.

Nota de capas: la resolución de membresía es el **gate de autorización** (infraestructura
transversal), por eso su consulta vive aquí y no en un repository de dominio. El acceso a
datos de negocio sí pasa siempre por repositories.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.db import get_session
from app.core.errors import ForbiddenError, NotFoundError
from app.models import Project, ProjectMembership, User, WorkspaceMembership
from app.models.enums import ProjectRole, WorkspaceRole


class Permission(StrEnum):
    """Acciones autorizables (workspace-level y project-level)."""

    # Workspace-level
    WORKSPACES_READ = "workspaces:read"
    WORKSPACES_UPDATE = "workspaces:update"
    WORKSPACES_DELETE = "workspaces:delete"
    WORKSPACES_MANAGE_MEMBERS = "workspaces:manage_members"
    WORKSPACES_TRANSFER_OWNERSHIP = "workspaces:transfer_ownership"
    PROJECTS_CREATE = "projects:create"  # crear un proyecto DENTRO del workspace

    # Project-level (se evalúan contra el rol EFECTIVO de proyecto)
    PROJECTS_READ = "projects:read"
    PROJECTS_UPDATE = "projects:update"
    PROJECTS_DELETE = "projects:delete"
    PROJECTS_MANAGE_MEMBERS = "projects:manage_members"


# ── Matriz de permisos de WORKSPACE: rol de workspace -> acciones (fuente única) ──
# (ADR-0002) guest no tiene overview del workspace: sin permisos a nivel workspace.
PERMISSION_MATRIX: dict[WorkspaceRole, frozenset[Permission]] = {
    WorkspaceRole.OWNER: frozenset(
        {
            Permission.WORKSPACES_READ,
            Permission.WORKSPACES_UPDATE,
            Permission.WORKSPACES_DELETE,
            Permission.WORKSPACES_MANAGE_MEMBERS,
            Permission.WORKSPACES_TRANSFER_OWNERSHIP,
            Permission.PROJECTS_CREATE,
        }
    ),
    WorkspaceRole.ADMIN: frozenset(
        {
            Permission.WORKSPACES_READ,
            Permission.WORKSPACES_UPDATE,
            Permission.WORKSPACES_MANAGE_MEMBERS,
            Permission.PROJECTS_CREATE,
        }
    ),
    WorkspaceRole.MEMBER: frozenset({Permission.WORKSPACES_READ}),
    WorkspaceRole.GUEST: frozenset(),
}

# ── Matriz de permisos de PROYECTO: rol de proyecto -> acciones (fuente única) ──
PROJECT_PERMISSION_MATRIX: dict[ProjectRole, frozenset[Permission]] = {
    ProjectRole.LEAD: frozenset(
        {
            Permission.PROJECTS_READ,
            Permission.PROJECTS_UPDATE,
            Permission.PROJECTS_DELETE,
            Permission.PROJECTS_MANAGE_MEMBERS,
        }
    ),
    ProjectRole.CONTRIBUTOR: frozenset({Permission.PROJECTS_READ, Permission.PROJECTS_UPDATE}),
    ProjectRole.VIEWER: frozenset({Permission.PROJECTS_READ}),
}


def has_permission(role: WorkspaceRole, action: Permission) -> bool:
    """True si el ``role`` de workspace puede ejecutar ``action`` según la matriz de workspace."""
    return action in PERMISSION_MATRIX.get(role, frozenset())


def has_project_permission(role: ProjectRole, action: Permission) -> bool:
    """True si el ``role`` **efectivo** de proyecto puede ejecutar ``action``."""
    return action in PROJECT_PERMISSION_MATRIX.get(role, frozenset())


def effective_project_role(
    workspace_role: WorkspaceRole, project_role: ProjectRole | None
) -> ProjectRole | None:
    """Rol efectivo sobre un proyecto (ADR-0002, "Rol efectivo e invariantes").

    - owner/admin: acceso implícito a todos los proyectos como **piso** = ``lead``; la
      membresía de proyecto solo puede sumar, nunca restar (y no hay nada sobre ``lead``).
    - member/guest: el acceso proviene **solo** de la membresía explícita; sin ella,
      ``None`` (sin acceso).
    """
    if workspace_role in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
        return ProjectRole.LEAD
    return project_role


# ───────────────────────────── Contexto de workspace ─────────────────────────────


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
        raise NotFoundError("Workspace no encontrado")
    return WorkspaceContext(user=user, workspace_id=workspace_id, workspace_role=membership.role)


def requiere_permiso(
    action: Permission,
) -> Callable[[WorkspaceContext], Awaitable[WorkspaceContext]]:
    """Dependencia que exige ``action`` sobre el workspace de la ruta (403 si no autorizado)."""

    async def checker(
        context: WorkspaceContext = Depends(get_workspace_context),
    ) -> WorkspaceContext:
        if not has_permission(context.workspace_role, action):
            raise ForbiddenError()
        return context

    return checker


# ───────────────────────────── Contexto de proyecto ─────────────────────────────


@dataclass(frozen=True)
class ProjectContext:
    """Contexto de autorización para una petición a un recurso de proyecto."""

    user: User
    workspace_id: UUID
    workspace_role: WorkspaceRole
    project_id: UUID
    effective_role: ProjectRole  # nunca None aquí: sin acceso efectivo -> 404 antes


async def get_project_context(
    project_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    session: AsyncSession = Depends(get_session),
) -> ProjectContext:
    """Resuelve el contexto de proyecto combinando rol de workspace + rol de proyecto.

    404 si el proyecto no existe, no pertenece al workspace, o el usuario no tiene **acceso
    efectivo** (member/guest sin membresía de proyecto) — así no se revela su existencia.
    """
    project = await session.get(Project, project_id)
    if project is None or project.workspace_id != workspace.workspace_id:
        raise NotFoundError("Proyecto no encontrado")

    stmt = select(ProjectMembership).where(
        ProjectMembership.project_id == project_id,
        ProjectMembership.user_id == workspace.user.user_id,
    )
    membership = (await session.execute(stmt)).scalar_one_or_none()
    effective = effective_project_role(
        workspace.workspace_role, membership.role if membership else None
    )
    if effective is None:
        raise NotFoundError("Proyecto no encontrado")

    return ProjectContext(
        user=workspace.user,
        workspace_id=workspace.workspace_id,
        workspace_role=workspace.workspace_role,
        project_id=project_id,
        effective_role=effective,
    )


def requiere_permiso_proyecto(
    action: Permission,
) -> Callable[[ProjectContext], Awaitable[ProjectContext]]:
    """Dependencia que exige ``action`` sobre el proyecto de la ruta (403 si no autorizado)."""

    async def checker(
        context: ProjectContext = Depends(get_project_context),
    ) -> ProjectContext:
        if not has_project_permission(context.effective_role, action):
            raise ForbiddenError()
        return context

    return checker
