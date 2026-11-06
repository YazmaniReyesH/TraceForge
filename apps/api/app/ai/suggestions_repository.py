"""Repositorio de sugerencias de IA y del mapeo de redacción cifrado (única capa que toca la BD).

Acotado a ``workspace_id``/``project_id`` del contexto de proyecto (gate ya aplicado en el router),
nunca del cliente → aislamiento por defecto. Las lecturas de sugerencias se filtran además por la
sesión. El mapeo cifrado solo se inserta (append-only).
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIRedactionMap, AISuggestion
from app.models.enums import AISuggestionKind, AISuggestionStatus


class AISuggestionRepository:
    """Acceso a datos de sugerencias de IA (y su mapeo de redacción cifrado) de un project."""

    def __init__(self, session: AsyncSession, *, workspace_id: UUID, project_id: UUID) -> None:
        self._db = session
        self._workspace_id = workspace_id
        self._project_id = project_id

    async def flush(self) -> None:
        await self._db.flush()

    def add_suggestion(
        self,
        *,
        session_id: UUID,
        kind: AISuggestionKind,
        suggested_content: str,
        suggested_payload: dict[str, Any],
        provider: str,
        model: str,
        prompt_version: str,
        ai_call_log_id: UUID | None,
        input_refs: dict[str, Any],
        redaction_count: int,
        created_by: UUID,
    ) -> AISuggestion:
        row = AISuggestion(
            ai_suggestion_id=uuid4(),
            workspace_id=self._workspace_id,
            project_id=self._project_id,
            session_id=session_id,
            kind=kind,
            status=AISuggestionStatus.PENDING,  # ADR-0003: nace pendiente
            suggested_content=suggested_content,
            suggested_payload=suggested_payload,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            ai_call_log_id=ai_call_log_id,
            input_refs=input_refs,
            redaction_count=redaction_count,
            created_by=created_by,
        )
        self._db.add(row)
        return row

    def add_redaction_map(
        self,
        *,
        session_id: UUID,
        ai_suggestion_id: UUID,
        ciphertext: str,
        scheme: str,
        marker_count: int,
        created_by: UUID,
    ) -> AIRedactionMap:
        row = AIRedactionMap(
            ai_redaction_map_id=uuid4(),
            workspace_id=self._workspace_id,
            project_id=self._project_id,
            session_id=session_id,
            ai_suggestion_id=ai_suggestion_id,
            ciphertext=ciphertext,
            scheme=scheme,
            marker_count=marker_count,
            created_by=created_by,
        )
        self._db.add(row)
        return row

    async def get_suggestion(self, session_id: UUID, suggestion_id: UUID) -> AISuggestion | None:
        """Sugerencia del project+sesión del contexto (aislamiento)."""
        stmt = select(AISuggestion).where(
            AISuggestion.ai_suggestion_id == suggestion_id,
            AISuggestion.session_id == session_id,
            AISuggestion.project_id == self._project_id,
        )
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def list_suggestions(self, session_id: UUID) -> Sequence[AISuggestion]:
        stmt = (
            select(AISuggestion)
            .where(
                AISuggestion.session_id == session_id,
                AISuggestion.project_id == self._project_id,
            )
            .order_by(AISuggestion.created_at)
        )
        return (await self._db.execute(stmt)).scalars().all()
