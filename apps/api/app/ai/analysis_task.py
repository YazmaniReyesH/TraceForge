"""AI task "analizar contexto de sesión" (F1-T4c): prompt versionado + salida de 4 bloques.

La IA **propone** una guía de 4 bloques a partir de la evidencia de la sesión **en el orden del
timeline**; el código **valida la forma** (``parse``) contra un JSON Schema estricto (ADR-0004)
antes de entregarla. Si la salida no cumple, se rechaza con ``AIInvalidOutputError`` (no se entrega
una guía con forma inválida; el intento se registra en la bitácora).

El análisis es **efímero** (ADR-0017): no es una sugerencia aprobable, es guía viva y desechable.
"""

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.ai.errors import AIInvalidOutputError
from app.models.enums import SessionPhase

ANALYSIS_PROMPT_VERSION = "session_analysis/v1"


class ComandoSugerido(BaseModel):
    """Un comando de validación sugerido y, opcional, para qué sirve."""

    model_config = ConfigDict(extra="ignore")

    comando: str = Field(min_length=1)
    para_que: str | None = None


class Evaluacion(BaseModel):
    """Bloque 2: evaluación del estado actual + evidencia observada (lista de puntos)."""

    model_config = ConfigDict(extra="ignore")

    estado_actual: str = Field(min_length=1)
    evidencia_observada: list[str] = Field(default_factory=list)


class SessionAnalysisOutput(BaseModel):
    """Salida estructurada de 4 bloques del análisis de contexto de sesión (ADR-0004).

    Campos extra se ignoran; los obligatorios (``siguiente_objetivo``, ``evaluacion.estado_actual``,
    ``fase_detectada``) deben venir o la salida se rechaza. Las listas pueden venir vacías (robustez
    ante variación del modelo), pero su forma se valida.
    """

    model_config = ConfigDict(extra="ignore")

    # Bloque 1
    siguiente_objetivo: str = Field(min_length=1)
    # Bloque 2
    evaluacion: Evaluacion
    # Bloque 3
    validacion_sugerida: list[ComandoSugerido] = Field(default_factory=list)
    # Bloque 4
    precauciones: list[str] = Field(default_factory=list)
    fase_detectada: SessionPhase


def _strip_code_fence(text: str) -> str:
    """Quita un envoltorio ```...``` (con o sin ``json``) si el modelo lo agregó."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    body = stripped[3:]
    if body[:4].lower() == "json":
        body = body[4:]
    end = body.rfind("```")
    if end != -1:
        body = body[:end]
    return body.strip()


def _extract_json_object(text: str) -> str:
    """Extrae el primer objeto JSON ``{...}`` del texto (defensivo ante prosa alrededor)."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise AIInvalidOutputError("La respuesta no contiene un objeto JSON")
    return text[start : end + 1]


def parse_analysis(text: str) -> tuple[dict[str, Any], SessionAnalysisOutput]:
    """Valida la forma de la salida del modelo. Devuelve (payload validado, modelo).

    Rechaza con ``AIInvalidOutputError`` si no es JSON o no cumple el schema (ADR-0004).
    """
    raw = _extract_json_object(_strip_code_fence(text))
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AIInvalidOutputError("La respuesta no es JSON válido") from exc
    if not isinstance(data, dict):
        raise AIInvalidOutputError("La respuesta JSON no es un objeto")
    try:
        model = SessionAnalysisOutput.model_validate(data)
    except ValidationError as exc:
        raise AIInvalidOutputError("La respuesta no cumple el esquema de 4 bloques") from exc
    return model.model_dump(mode="json"), model


_INSTRUCTION = (
    "Eres un analista de seguridad acompañando un pentest EN VIVO. Se te da la EVIDENCIA de una "
    "sesión (comandos, salidas y notas) EN EL ORDEN del timeline: ese orden es la secuencia real "
    "de trabajo; respétalo (no lo reordenes por fecha). A partir SOLO de esa evidencia —sin "
    "inventar datos que no estén— produce una guía breve y accionable, en español, con 4 bloques:\n"
    "1) siguiente_objetivo: el próximo objetivo razonable dado lo hecho hasta ahora.\n"
    "2) evaluacion: estado_actual (resumen) y evidencia_observada (puntos clave observados).\n"
    "3) validacion_sugerida: comandos concretos para avanzar/validar (cada uno con 'comando' y, si "
    "ayuda, 'para_que').\n"
    "4) precauciones: buenas prácticas/observaciones para ese objetivo; y fase_detectada, la fase "
    "del pentest inferida de la evidencia."
)
_OUTPUT_FORMAT = (
    "Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional ni formato markdown, con "
    "esta forma EXACTA:\n"
    '{"siguiente_objetivo": "<texto>", '
    '"evaluacion": {"estado_actual": "<texto>", "evidencia_observada": ["<punto>", ...]}, '
    '"validacion_sugerida": [{"comando": "<texto>", "para_que": "<texto o null>"}, ...], '
    '"precauciones": ["<punto>", ...], '
    '"fase_detectada": "<uno de: recon | enumeración | foothold | privesc | otra>"}'
)


def full_instruction() -> str:
    """Instrucción + directiva de salida JSON (confiable, va FUERA de la frontera de evidencia)."""
    return f"{_INSTRUCTION}\n\n{_OUTPUT_FORMAT}"
