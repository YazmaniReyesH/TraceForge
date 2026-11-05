"""Schemas del gateway de IA (F1-T3): estado y ping verificable."""

from uuid import UUID

from pydantic import BaseModel

from app.models.enums import AICallStatus


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
