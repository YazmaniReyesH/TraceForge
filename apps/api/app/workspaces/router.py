"""Router de workspaces (delgado). Endpoints mínimos que ejercitan la autorización."""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.core.security import Permission, WorkspaceContext, requiere_permiso
from app.models import User, Workspace
from app.workspaces.dependencies import get_workspace_service
from app.workspaces.schemas import WorkspaceCreate, WorkspaceRead
from app.workspaces.service import WorkspaceService

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])

# Dependencia de permiso como singleton de módulo (evita llamar al factory en el default).
_requiere_lectura = requiere_permiso(Permission.WORKSPACES_READ)


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
    """Detalle del workspace. Protegido: 404 si no eres miembro, 403 si tu rol no lee."""
    workspace = await service.get(context.workspace_id)
    if workspace is None:  # defensivo: la membresía implica que existe
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace no encontrado")
    return workspace
