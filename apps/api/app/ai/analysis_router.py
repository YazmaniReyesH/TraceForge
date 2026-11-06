"""Router del análisis de contexto de sesión (F1-T4c), bajo la jerarquía project→sesión.

Permisos por **rol efectivo** (ADR-0002): analizar → ``projects:update`` (contributor/lead; viewer
no, porque puede hacer una llamada **real y de pago** al proveedor); leer el último análisis →
``projects:read`` (viewer+, no llama a la API). CSRF (ADR-0010) en mutaciones. Aislamiento vía el
contexto de proyecto y el filtro por sesión. La respuesta NUNCA expone el mapeo cifrado ni valores.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.ai.analysis_service import SessionAnalysisService
from app.ai.dependencies import get_session_analysis_service
from app.ai.schemas import SessionAnalysisRead
from app.core.csrf import require_csrf
from app.core.security import Permission, requiere_permiso_proyecto

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/projects/{project_id}/sessions/{session_id}",
    tags=["ia"],
    dependencies=[Depends(require_csrf)],
)

_puede_leer = requiere_permiso_proyecto(Permission.PROJECTS_READ)
_puede_escribir = requiere_permiso_proyecto(Permission.PROJECTS_UPDATE)


@router.post(
    "/analyze",
    response_model=SessionAnalysisRead,
    dependencies=[Depends(_puede_escribir)],
)
async def analyze_session(
    session_id: UUID,
    force: bool = False,
    service: SessionAnalysisService = Depends(get_session_analysis_service),
) -> SessionAnalysisRead:
    """Analiza la evidencia activa de la sesión (orden de position) → guía de 4 bloques.

    Hash-guard: si el estado no cambió y no se pasa ``force=true``, devuelve el análisis guardado
    (``from_cache=true``) sin llamar a la API.
    """
    return await service.analyze(session_id=session_id, force=force)


@router.get(
    "/analysis",
    response_model=SessionAnalysisRead,
    dependencies=[Depends(_puede_leer)],
)
async def get_last_analysis(
    session_id: UUID,
    service: SessionAnalysisService = Depends(get_session_analysis_service),
) -> SessionAnalysisRead:
    """Devuelve el último análisis guardado de la sesión (sin llamar a la API). 404 si no hay."""
    return await service.get_last(session_id=session_id)
