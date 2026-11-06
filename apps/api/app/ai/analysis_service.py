"""Servicio del análisis de contexto de sesión (F1-T4c, ADR-0017): guía **efímera** de 4 bloques.

Circuito para una sesión:

    juntar ítems activos **en orden de position** → **redactar** (ADR-0005) → **hash-guard** (si el
    estado no cambió y no hay ``force``, devolver el caché SIN llamar a la API) → **ensamblar** con
    la evidencia como dato no confiable + **prompt caching** (F1-T3/ADR-0017) → llamar al
    **AIProvider** (modelo de ``ai_policy`` con fallback ``.env``) → **validar la forma** de los 4
    bloques (ADR-0004) → **cachear** por sesión (hash + procedencia) → **registrar** en la bitácora.

El resultado es guía viva y **desechable**: NO es una sugerencia aprobable (no hay accept/edit). No
conoce HTTP. El commit vive aquí. Las pruebas sustituyen el ``AIProvider`` por un doble (sin API).
"""

import hashlib
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.analysis_repository import SessionAnalysisRepository
from app.ai.analysis_task import (
    ANALYSIS_PROMPT_VERSION,
    SessionAnalysisOutput,
    full_instruction,
    parse_analysis,
)
from app.ai.crypto import RedactionCipher
from app.ai.errors import (
    AIInvalidOutputError,
    AINoAnalysisError,
    AINoEvidenceError,
    AINotConfiguredError,
    AIProviderError,
)
from app.ai.port import AIProvider
from app.ai.prompt import assemble_analysis_prompt
from app.ai.redaction import redact
from app.ai.repository import AICallLogRepository
from app.ai.schemas import SessionAnalysisRead
from app.core.errors import NotFoundError
from app.models import EvidenceItem, EvidenceItemVersion, SessionAnalysis
from app.models.enums import AICallStatus
from app.timeline.repository import TimelineRepository

_EvidenceRow = Row[tuple[EvidenceItem, EvidenceItemVersion]]


def _render_evidence(rows: Sequence[_EvidenceRow]) -> str:
    """Arma el texto crudo de la evidencia (antes de redactar), EN EL ORDEN recibido (position)."""
    blocks: list[str] = []
    for item, version in rows:
        if item.kind.value == "command":
            salida = version.command_output or ""
            blocks.append(f"$ {version.command_text or ''}\n{salida}".rstrip())
        else:
            blocks.append(f"[nota] {version.note_text or ''}".rstrip())
    return "\n\n".join(blocks)


def _state_hash(rows: Sequence[_EvidenceRow]) -> str:
    """Hash del **estado analizable**: (id, versión, posición) de cada ítem activo, en orden.

    Incluye la versión del prompt: subirla (v2) invalida los cachés previos y fuerza re-análisis.
    Reordenar/editar/borrar un ítem cambia este hash → el hash-guard vuelve a llamar.
    """
    parts = [f"prompt:{ANALYSIS_PROMPT_VERSION}"]
    for item, _ in rows:
        parts.append(f"{item.evidence_item_id}:{item.current_version}:{item.position}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


class SessionAnalysisService:
    """Analiza el contexto de una sesión y cachea el resultado (acceso ya gate'd por el router)."""

    def __init__(
        self,
        *,
        provider: AIProvider,
        cipher: RedactionCipher,
        timeline: TimelineRepository,
        log_repo: AICallLogRepository,
        analyses: SessionAnalysisRepository,
        session: AsyncSession,
        max_tokens: int,
        user_id: UUID,
    ) -> None:
        self._provider = provider
        self._cipher = cipher
        self._timeline = timeline
        self._log = log_repo
        self._analyses = analyses
        self._db = session
        self._max_tokens = max_tokens
        self._user_id = user_id

    async def analyze(self, *, session_id: UUID, force: bool = False) -> SessionAnalysisRead:
        """Analiza la sesión. Hash-guard: sin cambios y sin ``force`` → devuelve el caché."""
        if await self._timeline.get_session(session_id) is None:
            raise NotFoundError("Sesión no encontrada")
        rows = await self._timeline.list_items_with_current(session_id)  # orden por position
        if not rows:
            raise AINoEvidenceError

        state_hash = _state_hash(rows)
        existing = await self._analyses.get_by_session(session_id)
        if existing is not None and existing.state_hash == state_hash and not force:
            # Hash-guard: nada cambió → NO se llama a la API (ni se registra otra llamada).
            return self._to_read(existing, from_cache=True)

        red = redact(_render_evidence(rows))
        prompt = assemble_analysis_prompt(full_instruction(), red.text, boundary_seed=state_hash)
        sha = hashlib.sha256(prompt.user.encode("utf-8")).hexdigest()

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

        # ADR-0004: el código valida la FORMA (4 bloques) antes de entregar/cachear. Si no cumple,
        # se registra como error y se propaga; NO se entrega ni se cachea una guía inválida.
        try:
            payload, _model = parse_analysis(completion.text)
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

        # Llamada OK: bitácora (F1-T3) → id para la procedencia.
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
        await self._analyses.flush()  # asegura ai_call_log_id

        # Mapeo de redacción cifrado (ADR-0016): solo si hay secretos y clave (si no, NO en claro).
        ciphertext: str | None = None
        scheme: str | None = None
        if red.mapping and self._cipher.is_configured:
            ciphertext = self._cipher.encrypt_mapping(red.mapping)
            scheme = self._cipher.scheme

        row = self._upsert(
            existing=existing,
            session_id=session_id,
            state_hash=state_hash,
            result=payload,
            analyzed_item_count=len(rows),
            model=completion.model,
            ai_call_log_id=log_row.ai_call_log_id,
            redaction_count=red.count,
            redaction_ciphertext=ciphertext,
            redaction_scheme=scheme,
        )
        await self._db.commit()
        await self._db.refresh(row)  # trae created_at/updated_at generados por la base
        return self._to_read(row, from_cache=False)

    async def get_last(self, *, session_id: UUID) -> SessionAnalysisRead:
        """Devuelve el último análisis guardado (sin llamar a la API). 404 si no existe aún."""
        if await self._timeline.get_session(session_id) is None:
            raise NotFoundError("Sesión no encontrada")
        existing = await self._analyses.get_by_session(session_id)
        if existing is None:
            raise AINoAnalysisError
        return self._to_read(existing, from_cache=True)

    # ── Helpers ──
    def _upsert(
        self,
        *,
        existing: SessionAnalysis | None,
        session_id: UUID,
        state_hash: str,
        result: dict[str, object],
        analyzed_item_count: int,
        model: str,
        ai_call_log_id: UUID | None,
        redaction_count: int,
        redaction_ciphertext: str | None,
        redaction_scheme: str | None,
    ) -> SessionAnalysis:
        """Crea o **sobrescribe** la fila de caché de la sesión (una por sesión)."""
        if existing is None:
            return self._analyses.add(
                session_id=session_id,
                state_hash=state_hash,
                result=result,
                analyzed_item_count=analyzed_item_count,
                provider=self._provider.name,
                model=model,
                prompt_version=ANALYSIS_PROMPT_VERSION,
                ai_call_log_id=ai_call_log_id,
                redaction_count=redaction_count,
                redaction_ciphertext=redaction_ciphertext,
                redaction_scheme=redaction_scheme,
                created_by=self._user_id,
            )
        existing.state_hash = state_hash
        existing.result = result
        existing.analyzed_item_count = analyzed_item_count
        existing.provider = self._provider.name
        existing.model = model
        existing.prompt_version = ANALYSIS_PROMPT_VERSION
        existing.ai_call_log_id = ai_call_log_id
        existing.redaction_count = redaction_count
        existing.redaction_ciphertext = redaction_ciphertext
        existing.redaction_scheme = redaction_scheme
        existing.created_by = self._user_id
        return existing

    @staticmethod
    def _to_read(row: SessionAnalysis, *, from_cache: bool) -> SessionAnalysisRead:
        return SessionAnalysisRead(
            session_id=row.session_id,
            from_cache=from_cache,
            analyzed_item_count=row.analyzed_item_count,
            state_hash=row.state_hash,
            result=SessionAnalysisOutput.model_validate(row.result),
            provider=row.provider,
            model=row.model,
            prompt_version=row.prompt_version,
            ai_call_log_id=row.ai_call_log_id,
            redaction_count=row.redaction_count,
            redaction_map_stored=row.redaction_ciphertext is not None,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
