"""Router de sugerencias de IA (F1-T4a) — **APARCADO** en F1-T4c (ADR-0017).

Este flujo (``description``/``next_step`` persistidas con ``accept``/``edit``) se **aparca**: lo
sustituye el *análisis de contexto efímero* (``analysis_router.py``). Los endpoints quedan marcados
como **deprecados** (``deprecated=True`` → tachados en ``/docs``), pero **siguen montados** para no
romper nada que aún los consuma y por si se reutilizan en la fase de reporte. No borrar las tablas
``ai_suggestions``/``ai_redaction_maps`` (ADR-0017). Nada nuevo debería construirse sobre ellos.

Permisos por **rol efectivo** (ADR-0002): generar/aceptar/editar → ``projects:update``
(contributor/lead; viewer no); listar → ``projects:read`` (viewer+). CSRF (ADR-0010) en mutaciones.
Aislamiento vía el contexto de proyecto y el filtro por sesión. La respuesta NUNCA expone el mapeo
cifrado ni valores crudos.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.ai.dependencies import get_ai_suggestion_service
from app.ai.schemas import AISuggestionEdit, AISuggestionGenerate, AISuggestionRead
from app.ai.suggestions_service import AISuggestionService
from app.core.csrf import require_csrf
from app.core.security import Permission, requiere_permiso_proyecto

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/projects/{project_id}/sessions/{session_id}/suggestions",
    tags=["ia"],
    dependencies=[Depends(require_csrf)],
    deprecated=True,  # F1-T4c: flujo aparcado (ADR-0017); sustituido por el análisis de contexto.
)

_puede_leer = requiere_permiso_proyecto(Permission.PROJECTS_READ)
_puede_escribir = requiere_permiso_proyecto(Permission.PROJECTS_UPDATE)


@router.post(
    "",
    response_model=AISuggestionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_puede_escribir)],
)
async def generate_suggestion(
    session_id: UUID,
    data: AISuggestionGenerate,
    service: AISuggestionService = Depends(get_ai_suggestion_service),
) -> AISuggestionRead:
    """Genera una sugerencia (``description``|``next_step``) desde la evidencia de la sesión."""
    return await service.generate(session_id=session_id, kind=data.kind)


@router.get("", response_model=list[AISuggestionRead], dependencies=[Depends(_puede_leer)])
async def list_suggestions(
    session_id: UUID,
    service: AISuggestionService = Depends(get_ai_suggestion_service),
) -> list[AISuggestionRead]:
    return await service.list_suggestions(session_id=session_id)


@router.post(
    "/{suggestion_id}/accept",
    response_model=AISuggestionRead,
    dependencies=[Depends(_puede_escribir)],
)
async def accept_suggestion(
    session_id: UUID,
    suggestion_id: UUID,
    service: AISuggestionService = Depends(get_ai_suggestion_service),
) -> AISuggestionRead:
    """Acepta la sugerencia tal cual (pending → accepted)."""
    return await service.accept(session_id=session_id, suggestion_id=suggestion_id)


@router.post(
    "/{suggestion_id}/edit",
    response_model=AISuggestionRead,
    dependencies=[Depends(_puede_escribir)],
)
async def edit_suggestion(
    session_id: UUID,
    suggestion_id: UUID,
    data: AISuggestionEdit,
    service: AISuggestionService = Depends(get_ai_suggestion_service),
) -> AISuggestionRead:
    """Edita la sugerencia (pending|edited → edited), conservando el original + el rastro de IA."""
    return await service.edit(
        session_id=session_id, suggestion_id=suggestion_id, content=data.content
    )
