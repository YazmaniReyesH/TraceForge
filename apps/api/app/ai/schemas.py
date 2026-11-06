"""Schemas del gateway de IA: estado y ping (F1-T3); sugerencias de IA (F1-T4a)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AICallStatus, AISuggestionKind, AISuggestionStatus


class AIStatusRead(BaseModel):
    """Estado de configuración de la IA (sin llamar al proveedor)."""

    configured: bool
    provider: str
    model: str


class AIPingResult(BaseModel):
    """Resultado del ping: confirma el circuito redactar→ensamblar→llamar→registrar.

    Todo lo que devuelve es seguro (ya redactado): la ``redacted_evidence`` prueba que la redacción
    corrió, el ``assembled_user_prompt`` muestra la evidencia delimitada (anti-inyección), y
    ``response_text`` es la respuesta real de Claude cuando ``status=ok``.
    """

    ai_call_log_id: UUID
    status: AICallStatus
    configured: bool
    provider: str
    model: str
    redaction_count: int
    redacted_evidence: str
    assembled_user_prompt: str
    response_text: str | None
    input_tokens: int | None
    output_tokens: int | None
    error_code: str | None


# ── Sugerencias de IA (F1-T4a) ──


class AISuggestionGenerate(BaseModel):
    """Solicitud para generar una sugerencia sobre la evidencia de una sesión."""

    kind: AISuggestionKind


class AISuggestionEdit(BaseModel):
    """Edición humana de una sugerencia (pending|edited → edited). Conserva el original sugerido."""

    content: str = Field(min_length=1, max_length=100_000)


class AISuggestionRead(BaseModel):
    """Sugerencia de IA con su procedencia (ADR-0003). NUNCA expone el mapeo cifrado ni valores.

    ``suggested_content`` es el texto propuesto por la IA (inmutable); ``edited_content`` es la
    edición humana cuando ``status=edited``. ``suggested_payload`` es la salida estructurada ya
    validada (segura: se generó sobre evidencia redactada). ``input_refs`` referencia la evidencia.
    """

    model_config = ConfigDict(from_attributes=True)

    ai_suggestion_id: UUID
    session_id: UUID
    kind: AISuggestionKind
    status: AISuggestionStatus
    suggested_content: str
    suggested_payload: dict[str, Any]
    edited_content: str | None
    # Procedencia
    provider: str
    model: str
    prompt_version: str
    ai_call_log_id: UUID | None
    input_refs: dict[str, Any]
    redaction_count: int
    redaction_map_stored: bool
    # Auditoría de la transición
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
