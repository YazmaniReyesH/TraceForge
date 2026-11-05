"""Repositorio de la bitácora de IA (única capa que toca la BD). Acotado a workspace+project.

Aislamiento: el ``workspace_id``/``project_id`` salen del contexto de proyecto (gate ya aplicado en
el router), nunca del cliente. Solo inserta filas (la bitácora es append-only en la práctica).
"""

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AICallLog
from app.models.enums import AICallStatus


class AICallLogRepository:
    """Acceso a datos de la bitácora de llamadas de IA de un project."""

    def __init__(self, session: AsyncSession, *, workspace_id: UUID, project_id: UUID) -> None:
        self._db = session
        self._workspace_id = workspace_id
        self._project_id = project_id

    def add(
        self,
        *,
        provider: str,
        model: str,
        status: AICallStatus,
        created_by: UUID,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        redacted_prompt: str | None = None,
        redacted_prompt_sha256: str | None = None,
        redaction_count: int = 0,
        error_code: str | None = None,
    ) -> AICallLog:
        row = AICallLog(
            ai_call_log_id=uuid4(),
            workspace_id=self._workspace_id,
            project_id=self._project_id,
            provider=provider,
            model=model,
            status=status,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            redacted_prompt=redacted_prompt,
            redacted_prompt_sha256=redacted_prompt_sha256,
            redaction_count=redaction_count,
            error_code=error_code,
            created_by=created_by,
        )
        self._db.add(row)
        return row
