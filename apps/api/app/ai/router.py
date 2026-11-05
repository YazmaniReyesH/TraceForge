"""Router del gateway de IA (F1-T3): estado y ping verificable, bajo la jerarquía del project.

Permisos por **rol efectivo** (ADR-0002): estado → ``projects:read`` (viewer+); ping →
``projects:update`` (contributor/lead) porque hace una llamada **real y de pago** al proveedor y
**registra** en la bitácora. CSRF (ADR-0010) a nivel de router en mutaciones. El ping **siempre
responde 200** con un ``status`` (reporta el estado del circuito; no es el circuito en sí):
``ok`` / ``error`` / ``not_configured``.
"""

from fastapi import APIRouter, Depends, status

from app.ai.dependencies import get_ai_service
from app.ai.schemas import AIPingResult, AIStatusRead
from app.ai.service import AIService
from app.core.csrf import require_csrf
from app.core.security import Permission, requiere_permiso_proyecto

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/projects/{project_id}/ai",
    tags=["ia"],
    dependencies=[Depends(require_csrf)],
)

_puede_leer = requiere_permiso_proyecto(Permission.PROJECTS_READ)
_puede_escribir = requiere_permiso_proyecto(Permission.PROJECTS_UPDATE)


@router.get("/status", response_model=AIStatusRead, dependencies=[Depends(_puede_leer)])
async def ai_status(service: AIService = Depends(get_ai_service)) -> AIStatusRead:
    """Estado de configuración de la IA (no llama al proveedor, no cuesta)."""
    return service.status()


@router.post(
    "/ping",
    response_model=AIPingResult,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(_puede_escribir)],
)
async def ai_ping(service: AIService = Depends(get_ai_service)) -> AIPingResult:
    """Circuito completo con contenido sintético: redacta → ensambla → llama → registra."""
    return await service.ping()
