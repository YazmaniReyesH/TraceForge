"""Router de workspaces y de membresías de workspace (delgado).

Los errores de dominio se traducen al envelope ``{code, message}`` por el manejador central
(ADR-0009); el router no los captura. CSRF (ADR-0010) se exige a nivel de router en mutaciones.
"""

from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_user
from app.core.csrf import require_csrf
from app.core.errors import NotFoundError
from app.core.security import Permission, WorkspaceContext, requiere_permiso
from app.models import User, Workspace
from app.workspaces.dependencies import get_workspace_service
from app.workspaces.schemas import (
    TransferOwnershipRequest,
    WorkspaceCreate,
    WorkspaceMemberAdd,
    WorkspaceMemberRead,
    WorkspaceMemberRoleUpdate,
    WorkspaceRead,
)
from app.workspaces.service import WorkspaceService

router = APIRouter(
    prefix="/api/v1/workspaces",
    tags=["workspaces"],
    dependencies=[Depends(require_csrf)],  # CSRF en mutaciones (los GET se saltan solos)
)

# Dependencias de permiso como singletons de módulo (evita llamar al factory en el default).
_requiere_lectura = requiere_permiso(Permission.WORKSPACES_READ)
_gestiona_miembros = requiere_permiso(Permission.WORKSPACES_MANAGE_MEMBERS)
_transfiere = requiere_permiso(Permission.WORKSPACES_TRANSFER_OWNERSHIP)


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    data: WorkspaceCreate,
    user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
) -> Workspace:
    """Crea un workspace; el creador queda como ``owner`` (misma transacción)."""
    return await service.create(name=data.name, owner=user)


@router.get("", response_model=list[WorkspaceRead])
async def list_workspaces(
    user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
) -> Sequence[Workspace]:
    """Lista los workspaces del usuario actual (no muestra ajenos)."""
    return await service.list_for_user(user.user_id)


@router.get("/{workspace_id}", response_model=WorkspaceRead)
async def get_workspace(
    context: WorkspaceContext = Depends(_requiere_lectura),
    service: WorkspaceService = Depends(get_workspace_service),
) -> Workspace:
    """Detalle del workspace. 404 si no eres miembro, 403 si tu rol no lee."""
    workspace = await service.get(context.workspace_id)
    if workspace is None:  # defensivo: la membresía implica que existe
        raise NotFoundError("Workspace no encontrado")
    return workspace


# ── Membresías de workspace ──


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberRead])
async def list_members(
    context: WorkspaceContext = Depends(_requiere_lectura),
    service: WorkspaceService = Depends(get_workspace_service),
) -> list[WorkspaceMemberRead]:
    rows = await service.list_members(context.workspace_id)
    return [
        WorkspaceMemberRead(
            user_id=user.user_id,
            email=user.email,
            display_name=user.display_name,
            role=membership.role,
        )
        for user, membership in rows
    ]


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    data: WorkspaceMemberAdd,
    context: WorkspaceContext = Depends(_gestiona_miembros),
    service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceMemberRead:
    user, membership = await service.add_member(
        workspace_id=context.workspace_id, email=data.email, role=data.role
    )
    return WorkspaceMemberRead(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
        role=membership.role,
    )


@router.patch("/{workspace_id}/members/{user_id}", response_model=WorkspaceMemberRead)
async def change_member_role(
    user_id: UUID,
    data: WorkspaceMemberRoleUpdate,
    context: WorkspaceContext = Depends(_gestiona_miembros),
    service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceMemberRead:
    await service.change_member_role(
        workspace_id=context.workspace_id, user_id=user_id, role=data.role
    )
    for user, membership in await service.list_members(context.workspace_id):
        if membership.user_id == user_id:
            return WorkspaceMemberRead(
                user_id=user.user_id,
                email=user.email,
                display_name=user.display_name,
                role=membership.role,
            )
    raise NotFoundError("Miembro no encontrado")


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: UUID,
    context: WorkspaceContext = Depends(_gestiona_miembros),
    service: WorkspaceService = Depends(get_workspace_service),
) -> None:
    await service.remove_member(workspace_id=context.workspace_id, user_id=user_id)


@router.post("/{workspace_id}/transfer-ownership", status_code=status.HTTP_204_NO_CONTENT)
async def transfer_ownership(
    data: TransferOwnershipRequest,
    context: WorkspaceContext = Depends(_transfiere),
    service: WorkspaceService = Depends(get_workspace_service),
) -> None:
    """Transfiere la propiedad a otro miembro (atómico). Solo el owner actual puede."""
    await service.transfer_ownership(
        workspace_id=context.workspace_id,
        current_owner_id=context.user.user_id,
        new_owner_id=data.new_owner_user_id,
    )
