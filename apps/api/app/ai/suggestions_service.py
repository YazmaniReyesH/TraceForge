"""Servicio de sugerencias de IA (F1-T4a): la primera función de IA de producto.

Orquesta el patrón fundacional (ADR-0003/0004/0005) para una sesión:

    juntar evidencia → **redactar** (ADR-0005) → **persistir el mapeo cifrado** (ADR-0016) →
    **ensamblar** el prompt con la evidencia como dato no confiable → llamar al **AIProvider**
    pidiendo **salida estructurada** → **validar la forma** (ADR-0004) → persistir la sugerencia en
    ``pending`` con **procedencia completa** (ADR-0003) → **registrar** en la bitácora (F1-T3).

La IA **propone**; el humano **acepta** o **edita** (máquina de estados con auditoría). El contenido
sugerido original nunca se sobrescribe y la evidencia cruda jamás se sustituye por la narrativa.

No conoce HTTP. El commit de la unidad de trabajo vive aquí. Las pruebas sustituyen el
``AIProvider`` por un doble (no se llama a la API real).
"""

import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.crypto import RedactionCipher
from app.ai.errors import (
    AIInvalidOutputError,
    AINoEvidenceError,
    AINotConfiguredError,
    AIProviderError,
    AISuggestionInvalidTransitionError,
)
from app.ai.port import AIProvider
from app.ai.prompt import assemble_prompt
from app.ai.redaction import redact
from app.ai.repository import AICallLogRepository
from app.ai.schemas import AISuggestionRead
from app.ai.suggestions_repository import AISuggestionRepository
from app.ai.tasks import TASKS
from app.core.errors import NotFoundError
from app.models import AISuggestion, EvidenceItem, EvidenceItemVersion
from app.models.enums import AICallStatus, AISuggestionKind, AISuggestionStatus
from app.timeline.repository import TimelineRepository

# Máquina de estados (ADR-0003): nace pending; pending→accepted/edited; edited admite re-edición;
# accepted es terminal. Cualquier otra transición es un error de dominio (409).
_TRANSITIONS: dict[AISuggestionStatus, frozenset[AISuggestionStatus]] = {
    AISuggestionStatus.PENDING: frozenset({AISuggestionStatus.ACCEPTED, AISuggestionStatus.EDITED}),
    AISuggestionStatus.EDITED: frozenset({AISuggestionStatus.EDITED}),
    AISuggestionStatus.ACCEPTED: frozenset(),
}


def _render_evidence(rows: Sequence[Row[tuple[EvidenceItem, EvidenceItemVersion]]]) -> str:
    """Arma el texto crudo de la evidencia (antes de redactar), en orden del timeline."""
    blocks: list[str] = []
    for item, version in rows:
        if item.kind.value == "command":
            salida = version.command_output or ""
            blocks.append(f"$ {version.command_text or ''}\n{salida}".rstrip())
        else:
            blocks.append(f"[nota] {version.note_text or ''}".rstrip())
    return "\n\n".join(blocks)


class AISuggestionService:
    """Genera y transiciona sugerencias de IA de una sesión (acceso ya gate'd por el router)."""

    def __init__(
        self,
        *,
        provider: AIProvider,
        cipher: RedactionCipher,
        timeline: TimelineRepository,
        log_repo: AICallLogRepository,
        suggestions: AISuggestionRepository,
        session: AsyncSession,
        max_tokens: int,
        user_id: UUID,
    ) -> None:
        self._provider = provider
        self._cipher = cipher
        self._timeline = timeline
        self._log = log_repo
        self._suggestions = suggestions
        self._db = session
        self._max_tokens = max_tokens
        self._user_id = user_id

    async def generate(self, *, session_id: UUID, kind: AISuggestionKind) -> AISuggestionRead:
        """Genera una sugerencia ``pending`` a partir de la evidencia redactada de la sesión."""
        session = await self._timeline.get_session(session_id)
        if session is None:
            raise NotFoundError("Sesión no encontrada")
        rows = await self._timeline.list_items_with_current(session_id)
        if not rows:
            raise AINoEvidenceError

        red = redact(_render_evidence(rows))
        task = TASKS[kind]
        prompt = assemble_prompt(task.full_instruction(), red.text)
        sha = hashlib.sha256(prompt.user.encode("utf-8")).hexdigest()
        input_refs = {
            "session_id": str(session_id),
            "evidence": [
                {"evidence_item_id": str(item.evidence_item_id), "version": item.current_version}
                for item, _ in rows
            ],
        }

        # IA no configurada: se registra el intento (auditoría) y se degrada con claridad.
        if not self._provider.is_configured:
            self._log.add(
                provider=self._provider.name,
                model=self._provider.model,
                status=AICallStatus.NOT_CONFIGURED,
                created_by=self._user_id,
                redacted_prompt=prompt.user,
                redacted_prompt_sha256=sha,
                redaction_count=red.count,
            )
            await self._db.commit()
            raise AINotConfiguredError

        # Error de red/API del proveedor: se registra (sin secretos) y se propaga.
        try:
            completion = await self._provider.complete(prompt, max_tokens=self._max_tokens)
        except AIProviderError as exc:
            self._log.add(
                provider=self._provider.name,
                model=self._provider.model,
                status=AICallStatus.ERROR,
                created_by=self._user_id,
                redacted_prompt=prompt.user,
                redacted_prompt_sha256=sha,
                redaction_count=red.count,
                error_code=exc.code,
            )
            await self._db.commit()
            raise

        # ADR-0004: el código valida la FORMA de la salida antes de persistir. Si no cumple el
        # schema, se registra como error (con tokens/modelo reales) y se propaga; no se persiste.
        try:
            payload, content = task.parse(completion.text)
        except AIInvalidOutputError as exc:
            self._log.add(
                provider=self._provider.name,
                model=completion.model,
                status=AICallStatus.ERROR,
                created_by=self._user_id,
                input_tokens=completion.input_tokens,
                output_tokens=completion.output_tokens,
                redacted_prompt=prompt.user,
                redacted_prompt_sha256=sha,
                redaction_count=red.count,
                error_code=exc.code,
            )
            await self._db.commit()
            raise

        # Llamada OK: se registra en la bitácora (F1-T3) y se obtiene el id para la procedencia.
        log_row = self._log.add(
            provider=self._provider.name,
            model=completion.model,
            status=AICallStatus.OK,
            created_by=self._user_id,
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
            redacted_prompt=prompt.user,
            redacted_prompt_sha256=sha,
            redaction_count=red.count,
        )
        await self._suggestions.flush()  # asegura ai_call_log_id (FK de la sugerencia)

        suggestion = self._suggestions.add_suggestion(
            session_id=session_id,
            kind=kind,
            suggested_content=content,
            suggested_payload=payload,
            provider=self._provider.name,
            model=completion.model,
            prompt_version=task.prompt_version,
            ai_call_log_id=log_row.ai_call_log_id,
            input_refs=input_refs,
            redaction_count=red.count,
            created_by=self._user_id,
        )
        await self._suggestions.flush()  # asegura ai_suggestion_id (FK del mapeo)

        # Mapeo de redacción cifrado (ADR-0016): solo si hay secretos y hay clave. Si no hay clave,
        # NO se persiste (jamás en claro) y queda marcado para que la UI avise (degradación segura).
        if red.mapping and self._cipher.is_configured:
            token = self._cipher.encrypt_mapping(red.mapping)
            self._suggestions.add_redaction_map(
                session_id=session_id,
                ai_suggestion_id=suggestion.ai_suggestion_id,
                ciphertext=token,
                scheme=self._cipher.scheme,
                marker_count=red.count,
                created_by=self._user_id,
            )
            suggestion.redaction_map_stored = True

        await self._db.commit()
        return await self._read(suggestion)

    async def list_suggestions(self, *, session_id: UUID) -> list[AISuggestionRead]:
        await self._require_session(session_id)
        rows = await self._suggestions.list_suggestions(session_id)
        return [AISuggestionRead.model_validate(s) for s in rows]

    async def accept(self, *, session_id: UUID, suggestion_id: UUID) -> AISuggestionRead:
        """Transición pending → accepted (toma la sugerencia tal cual)."""
        suggestion = await self._require_suggestion(session_id, suggestion_id)
        self._transition(suggestion, AISuggestionStatus.ACCEPTED)
        self._stamp_review(suggestion)
        await self._db.commit()
        return await self._read(suggestion)

    async def edit(
        self, *, session_id: UUID, suggestion_id: UUID, content: str
    ) -> AISuggestionRead:
        """pending|edited → edited. Guarda el texto humano y conserva el original + el rastro IA."""
        suggestion = await self._require_suggestion(session_id, suggestion_id)
        self._transition(suggestion, AISuggestionStatus.EDITED)
        suggestion.edited_content = content  # el suggested_content original NO se toca
        self._stamp_review(suggestion)
        await self._db.commit()
        return await self._read(suggestion)

    # ── Helpers ──
    async def _read(self, suggestion: AISuggestion) -> AISuggestionRead:
        """Serializa la sugerencia tras el commit.

        ``updated_at`` es un valor **generado por la base** (``server_default`` + ``onupdate``):
        tras el flush/commit queda **expirado** en la instancia, así que leerlo en el
        ``model_validate`` (síncrono) dispararía una recarga perezosa (I/O) fuera del greenlet
        async → ``MissingGreenlet``. Un ``refresh`` explícito trae ese valor **dentro** del
        contexto async antes de serializar. (``expire_on_commit=False`` ya evita expirar el
        resto; esto cubre solo lo que la base recalcula.)
        """
        await self._db.refresh(suggestion)
        return AISuggestionRead.model_validate(suggestion)

    def _stamp_review(self, suggestion: AISuggestion) -> None:
        suggestion.reviewed_by = self._user_id
        suggestion.reviewed_at = datetime.now(UTC)

    @staticmethod
    def _transition(suggestion: AISuggestion, target: AISuggestionStatus) -> None:
        if target not in _TRANSITIONS.get(suggestion.status, frozenset()):
            raise AISuggestionInvalidTransitionError
        suggestion.status = target

    async def _require_session(self, session_id: UUID) -> None:
        if await self._timeline.get_session(session_id) is None:
            raise NotFoundError("Sesión no encontrada")

    async def _require_suggestion(self, session_id: UUID, suggestion_id: UUID) -> AISuggestion:
        suggestion = await self._suggestions.get_suggestion(session_id, suggestion_id)
        if suggestion is None:
            raise NotFoundError("Sugerencia no encontrada")
        return suggestion
