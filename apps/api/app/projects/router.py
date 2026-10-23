"""Router de projects y de membresías de proyecto (delgado).

Errores de dominio → envelope central (ADR-0009); CSRF a nivel de router (ADR-0010).
"""

from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.csrf import require_csrf
from app.core.errors import NotFoundError
from app.core.security import (
    Permission,
    ProjectContext,
    WorkspaceContext,
    get_workspace_context,
    requiere_permiso,
    requiere_permiso_proyecto,
)
from app.models import Project
from app.projects.dependencies import get_project_service
from app.projects.schemas import (
    ProjectCreate,
    ProjectMemberAdd,
    ProjectMemberRead,
    ProjectMemberRoleUpdate,
    ProjectRead,
    ProjectUpdate,
)
from app.projects.service import ProjectService

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/projects",
    tags=["projects"],
    dependencies=[Depends(require_csrf)],  # CSRF en mutaciones (los GET se saltan solos)
)

# Dependencias de permiso como singletons de módulo (evita B008).
_puede_crear = requiere_permiso(Permission.PROJECTS_CREATE)
_puede_leer = requiere_permiso_proyecto(Permission.PROJECTS_READ)
_puede_editar = requiere_permiso_proyecto(Permission.PROJECTS_UPDATE)
_puede_borrar = requiere_permiso_proyecto(Permission.PROJECTS_DELETE)
_puede_gestionar_miembros = requiere_permiso_proyecto(Permission.PROJECTS_MANAGE_MEMBERS)


# ── CRUD de projects ──


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    context: WorkspaceContext = Depends(_puede_crear),
    service: ProjectService = Depends(get_project_service),
) -> Project:
    return await service.create(name=data.name, classification=data.classification)


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    context: WorkspaceContext = Depends(get_workspace_context),
    service: ProjectService = Depends(get_project_service),
) -> Sequence[Project]:
    """owner/admin ven todos; member/guest solo los proyectos donde son miembros."""
    return await service.list_visible(context)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    context: ProjectContext = Depends(_puede_leer),
    service: ProjectService = Depends(get_project_service),
) -> Project:
    project = await service.get(context.project_id)
    if project is None:  # defensivo: el contexto ya validó existencia/acceso
        raise NotFoundError("Proyecto no encontrado")
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    data: ProjectUpdate,
    context: ProjectContext = Depends(_puede_editar),
    service: ProjectService = Depends(get_project_service),
) -> Project:
    project = await service.update(context.project_id, data)
    if project is None:
        raise NotFoundError("Proyecto no encontrado")
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    context: ProjectContext = Depends(_puede_borrar),
    service: ProjectService = Depends(get_project_service),
) -> None:
    await service.delete(context.project_id)


# ── Membresías de proyecto ──


@router.get("/{project_id}/members", response_model=list[ProjectMemberRead])
async def list_project_members(
    context: ProjectContext = Depends(_puede_leer),
    service: ProjectService = Depends(get_project_service),
) -> list[ProjectMemberRead]:
    rows = await service.list_members(context.project_id)
    return [
        ProjectMemberRead(
            user_id=user.user_id,
            email=user.email,
            display_name=user.display_name,
            role=membership.role,
        )
        for user, membership in rows
    ]


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_project_member(
    data: ProjectMemberAdd,
    context: ProjectContext = Depends(_puede_gestionar_miembros),
    service: ProjectService = Depends(get_project_service),
) -> ProjectMemberRead:
    user, membership = await service.add_member(
        project_id=context.project_id, email=data.email, role=data.role
    )
    return ProjectMemberRead(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
        role=membership.role,
    )


@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberRead)
async def change_project_member_role(
    user_id: UUID,
    data: ProjectMemberRoleUpdate,
    context: ProjectContext = Depends(_puede_gestionar_miembros),
    service: ProjectService = Depends(get_project_service),
) -> ProjectMemberRead:
    membership = await service.change_member_role(
        project_id=context.project_id, user_id=user_id, role=data.role
    )
    if membership is None:
        raise NotFoundError("Miembro no encontrado")
    for user, m in await service.list_members(context.project_id):
        if m.user_id == user_id:
            return ProjectMemberRead(
                user_id=user.user_id,
                email=user.email,
                display_name=user.display_name,
                role=m.role,
            )
    raise NotFoundError("Miembro no encontrado")


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    user_id: UUID,
    context: ProjectContext = Depends(_puede_gestionar_miembros),
    service: ProjectService = Depends(get_project_service),
) -> None:
    removed = await service.remove_member(project_id=context.project_id, user_id=user_id)
    if not removed:
        raise NotFoundError("Miembro no encontrado")
