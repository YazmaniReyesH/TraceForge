"""Dependencias FastAPI del gateway de IA (inyección de capas sobre el contexto de proyecto)."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.claude_provider import ClaudeProvider
from app.ai.port import AIProvider
from app.ai.repository import AICallLogRepository
from app.ai.service import AIService
from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.core.security import ProjectContext, get_project_context


def get_ai_provider(settings: Settings = Depends(get_settings)) -> AIProvider:
    """Proveedor de IA (hoy, Claude).

    OpenAI/Gemini (F4) serían otra implementación de ``AIProvider`` seleccionada aquí (p. ej. según
    settings o la política de IA del proyecto). Las pruebas sustituyen esta dependencia por un doble
    del puerto para no llamar a la API real.
    """
    return ClaudeProvider(settings)


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
