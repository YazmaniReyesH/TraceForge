"""Router del timeline: sesiones e ítems de evidencia, bajo la jerarquía del project.

Permisos por **rol efectivo** (ADR-0002): leer -> ``projects:read`` (viewer+); crear/editar/borrar
-> ``projects:update`` (contributor/lead). CSRF (ADR-0010) a nivel de router en mutaciones. Errores
de dominio -> envelope central (ADR-0009). "Editar" versiona; borrar es soft-delete.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.csrf import require_csrf
from app.core.security import Permission, requiere_permiso_proyecto
from app.timeline.dependencies import get_timeline_service
from app.timeline.schemas import (
    EvidenceItemCreate,
    EvidenceItemMove,
    EvidenceItemRead,
    SessionCreate,
    SessionRead,
    SessionUpdate,
)
from app.timeline.service import TimelineService

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/projects/{project_id}/sessions",
    tags=["timeline"],
    dependencies=[Depends(require_csrf)],
)

_puede_leer = requiere_permiso_proyecto(Permission.PROJECTS_READ)
_puede_escribir = requiere_permiso_proyecto(Permission.PROJECTS_UPDATE)


# ── Sesiones ──


@router.post(
    "",
    response_model=SessionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_puede_escribir)],
)
async def create_session(
    data: SessionCreate,
    service: TimelineService = Depends(get_timeline_service),
) -> SessionRead:
    return await service.create_session(name=data.name)


@router.get("", response_model=list[SessionRead], dependencies=[Depends(_puede_leer)])
async def list_sessions(
    service: TimelineService = Depends(get_timeline_service),
) -> list[SessionRead]:
    return await service.list_sessions()


@router.patch("/{session_id}", response_model=SessionRead, dependencies=[Depends(_puede_escribir)])
async def rename_session(
    session_id: UUID,
    data: SessionUpdate,
    service: TimelineService = Depends(get_timeline_service),
) -> SessionRead:
    return await service.rename_session(session_id=session_id, name=data.name)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(_puede_escribir)],
)
async def delete_session(
    session_id: UUID,
    service: TimelineService = Depends(get_timeline_service),
) -> None:
    await service.delete_session(session_id=session_id)


# ── Ítems de evidencia ──


@router.post(
    "/{session_id}/items",
    response_model=EvidenceItemRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_puede_escribir)],
)
async def add_item(
    session_id: UUID,
    data: EvidenceItemCreate,
    service: TimelineService = Depends(get_timeline_service),
) -> EvidenceItemRead:
    return await service.add_item(
        session_id=session_id, data=data, after_item_id=data.after_item_id
    )


@router.get(
    "/{session_id}/items",
    response_model=list[EvidenceItemRead],
    dependencies=[Depends(_puede_leer)],
)
async def list_items(
    session_id: UUID,
    service: TimelineService = Depends(get_timeline_service),
) -> list[EvidenceItemRead]:
    return await service.list_items(session_id=session_id)


@router.get(
    "/{session_id}/items/{item_id}",
    response_model=None,
    dependencies=[Depends(_puede_leer)],
)
async def get_item(
    session_id: UUID,
    item_id: UUID,
    service: TimelineService = Depends(get_timeline_service),
    include_history: bool = False,
) -> EvidenceItemRead:
    """Detalle del ítem (versión vigente); con ``?include_history=true`` incluye el historial."""
    return await service.get_item(
        session_id=session_id, item_id=item_id, include_history=include_history
    )


@router.patch(
    "/{session_id}/items/{item_id}",
    response_model=EvidenceItemRead,
    dependencies=[Depends(_puede_escribir)],
)
async def edit_item(
    session_id: UUID,
    item_id: UUID,
    data: EvidenceItemCreate,
    service: TimelineService = Depends(get_timeline_service),
) -> EvidenceItemRead:
    """Edición = versión NUEVA (append-only); conserva el historial."""
    return await service.edit_item(session_id=session_id, item_id=item_id, data=data)


@router.patch(
    "/{session_id}/items/{item_id}/move",
    response_model=EvidenceItemRead,
    dependencies=[Depends(_puede_escribir)],
)
async def move_item(
    session_id: UUID,
    item_id: UUID,
    data: EvidenceItemMove,
    service: TimelineService = Depends(get_timeline_service),
) -> EvidenceItemRead:
    """Reordena el ítem (solo cambia el orden; no versiona ni toca el hash)."""
    return await service.move_item(
        session_id=session_id, item_id=item_id, after_item_id=data.after_item_id
    )


@router.delete(
    "/{session_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(_puede_escribir)],
)
async def delete_item(
    session_id: UUID,
    item_id: UUID,
    service: TimelineService = Depends(get_timeline_service),
) -> None:
    await service.delete_item(session_id=session_id, item_id=item_id)
