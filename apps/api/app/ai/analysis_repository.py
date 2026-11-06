"""Repositorio del caché de análisis de sesión (única capa que toca la BD). Acotado al project.

Aislamiento: ``workspace_id``/``project_id`` salen del contexto de proyecto (gate en el router), no
del cliente. Una fila por sesión (UNIQUE ``session_id``): el servicio decide si crea o actualiza.
"""

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SessionAnalysis


class SessionAnalysisRepository:
    """Acceso a datos del análisis de contexto (caché) de las sesiones de un project."""

    def __init__(self, session: AsyncSession, *, workspace_id: UUID, project_id: UUID) -> None:
        self._db = session
        self._workspace_id = workspace_id
        self._project_id = project_id

    async def flush(self) -> None:
        await self._db.flush()

    async def get_by_session(self, session_id: UUID) -> SessionAnalysis | None:
        """Último análisis de la sesión en el project del contexto (aislamiento)."""
        stmt = select(SessionAnalysis).where(
            SessionAnalysis.session_id == session_id,
            SessionAnalysis.project_id == self._project_id,
        )
        return (await self._db.execute(stmt)).scalar_one_or_none()

    def add(
        self,
        *,
        session_id: UUID,
        state_hash: str,
        result: dict[str, Any],
        analyzed_item_count: int,
        provider: str,
        model: str,
        prompt_version: str,
        ai_call_log_id: UUID | None,
        redaction_count: int,
        redaction_ciphertext: str | None,
        redaction_scheme: str | None,
        created_by: UUID,
    ) -> SessionAnalysis:
        row = SessionAnalysis(
            ai_session_analysis_id=uuid4(),
            workspace_id=self._workspace_id,
            project_id=self._project_id,
            session_id=session_id,
            state_hash=state_hash,
            result=result,
            analyzed_item_count=analyzed_item_count,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            ai_call_log_id=ai_call_log_id,
            redaction_count=redaction_count,
            redaction_ciphertext=redaction_ciphertext,
            redaction_scheme=redaction_scheme,
            created_by=created_by,
        )
        self._db.add(row)
        return row
