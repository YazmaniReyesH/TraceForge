"""Dependencias FastAPI del gateway de IA (inyección de capas sobre el contexto de proyecto)."""

from typing import Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.analysis_repository import SessionAnalysisRepository
from app.ai.analysis_service import SessionAnalysisService
from app.ai.claude_provider import ClaudeProvider
from app.ai.crypto import RedactionCipher
from app.ai.port import AIProvider
from app.ai.repository import AICallLogRepository
from app.ai.service import AIService
from app.ai.suggestions_repository import AISuggestionRepository
from app.ai.suggestions_service import AISuggestionService
from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.core.security import ProjectContext, get_project_context
from app.models import Project
from app.timeline.repository import TimelineRepository


def select_provider(settings: Settings, ai_policy: dict[str, Any] | None) -> AIProvider:
    """Elige el proveedor leyendo la ``ai_policy`` del proyecto, con el ``.env`` como fallback.

    Hoy solo existe Claude; ``ai_policy.provider`` queda **reservado** como base de la futura
    selección desde UI (otras implementaciones de ``AIProvider`` entrarían aquí, F4). Si la política
    trae ``model``, se usa ese; si no, ``TF_ANTHROPIC_MODEL``. No construye lógica compleja de
    política (eso es futuro): solo consulta y cae al default.
    """
    policy = ai_policy or {}
    model = policy.get("model")
    model = model if isinstance(model, str) and model else None
    return ClaudeProvider(settings, model=model)


async def get_ai_provider(
    context: ProjectContext = Depends(get_project_context),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AIProvider:
    """Proveedor de IA del proyecto (Claude), según su ``ai_policy`` o el ``.env``.

    Las pruebas sustituyen esta dependencia por un doble del puerto para no llamar a la API real.
    """
    project = await session.get(Project, context.project_id)
    ai_policy = project.ai_policy if project is not None else None
    return select_provider(settings, ai_policy)


def get_redaction_cipher(settings: Settings = Depends(get_settings)) -> RedactionCipher:
    """Cifrador del mapeo de redacción (Fernet). No configurado si falta ``TF_ENCRYPTION_KEY``."""
    return RedactionCipher(settings.encryption_key)


def get_ai_service(
    context: ProjectContext = Depends(get_project_context),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    provider: AIProvider = Depends(get_ai_provider),
) -> AIService:
    # workspace_id/project_id y user salen del contexto (gate ya aplicado en el router).
    repository = AICallLogRepository(
        session, workspace_id=context.workspace_id, project_id=context.project_id
    )
    return AIService(
        provider,
        repository,
        session,
        max_tokens=settings.anthropic_max_tokens,
        user_id=context.user.user_id,
    )


def get_ai_suggestion_service(
    context: ProjectContext = Depends(get_project_context),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    provider: AIProvider = Depends(get_ai_provider),
    cipher: RedactionCipher = Depends(get_redaction_cipher),
) -> AISuggestionService:
    # Los ids de aislamiento y la identidad salen del contexto (gate ya aplicado en el router).
    log_repo = AICallLogRepository(
        session, workspace_id=context.workspace_id, project_id=context.project_id
    )
    suggestion_repo = AISuggestionRepository(
        session, workspace_id=context.workspace_id, project_id=context.project_id
    )
    timeline_repo = TimelineRepository(session, context.project_id)
    return AISuggestionService(
        provider=provider,
        cipher=cipher,
        timeline=timeline_repo,
        log_repo=log_repo,
        suggestions=suggestion_repo,
        session=session,
        max_tokens=settings.anthropic_max_tokens,
        user_id=context.user.user_id,
    )


def get_session_analysis_service(
    context: ProjectContext = Depends(get_project_context),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    provider: AIProvider = Depends(get_ai_provider),
    cipher: RedactionCipher = Depends(get_redaction_cipher),
) -> SessionAnalysisService:
    # Ids de aislamiento e identidad salen del contexto (gate ya aplicado en el router).
    log_repo = AICallLogRepository(
        session, workspace_id=context.workspace_id, project_id=context.project_id
    )
    analysis_repo = SessionAnalysisRepository(
        session, workspace_id=context.workspace_id, project_id=context.project_id
    )
    timeline_repo = TimelineRepository(session, context.project_id)
    return SessionAnalysisService(
        provider=provider,
        cipher=cipher,
        timeline=timeline_repo,
        log_repo=log_repo,
        analyses=analysis_repo,
        session=session,
        max_tokens=settings.anthropic_analysis_max_tokens,
        user_id=context.user.user_id,
    )
