"""Registro de **AI tasks** de producto (F1-T4a) y el patrón sugerir→validar (ADR-0004).

Cada tarea de IA se define como una entrada de datos: su ``kind``, la **versión del prompt**, la
instrucción (confiable, va FUERA de la frontera de evidencia), el **modelo de salida estructurada**
(JSON Schema estricto) y cómo extraer el texto canónico de la salida validada. Agregar una función
es agregar una entrada aquí (y su registro en ``docs/ai-tasks.md``), no inventar un flujo nuevo.

La IA **propone** salida estructurada; el código **valida la forma** (``parse``) antes de persistir.
Si la salida no cumple el schema, se rechaza con ``AIInvalidOutputError`` (nunca se persiste una
sugerencia con forma inválida). En esta tanda no hay identificadores (CWE/CVE/…) que validar contra
catálogo — eso es F2 —, pero el patrón de validación determinista queda listo.
"""

import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.ai.errors import AIInvalidOutputError
from app.models.enums import AISuggestionKind


class AIOutput(BaseModel):
    """Base de las salidas estructuradas: expone el **texto canónico** de la sugerencia."""

    @property
    def content(self) -> str:
        raise NotImplementedError


class DescriptionOutput(AIOutput):
    """Salida estructurada de ``description``: una descripción de la evidencia de la sesión."""

    description: str = Field(min_length=1)

    @property
    def content(self) -> str:
        return self.description


class NextStepOutput(AIOutput):
    """Salida estructurada de ``next_step``: el siguiente paso sugerido + su justificación."""

    next_step: str = Field(min_length=1)
    rationale: str = Field(min_length=1)

    @property
    def content(self) -> str:
        return self.next_step


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


@dataclass(frozen=True)
class AITask:
    """Una función de IA: prompt versionado + salida estructurada validada."""

    kind: AISuggestionKind
    prompt_version: str
    instruction: str  # tarea confiable (va fuera de la frontera de evidencia)
    output_format: str  # directiva de forma JSON (se concatena a la instrucción)
    output_model: type[AIOutput]

    def full_instruction(self) -> str:
        """Instrucción + directiva de salida JSON (todo confiable, fuera de la evidencia)."""
        return f"{self.instruction}\n\n{self.output_format}"

    def parse(self, text: str) -> tuple[dict[str, Any], str]:
        """Valida la forma de la salida del modelo. Devuelve (payload validado, texto canónico).

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
            model = self.output_model.model_validate(data)
        except ValidationError as exc:
            raise AIInvalidOutputError("La respuesta no cumple el esquema esperado") from exc
        return model.model_dump(), model.content


_DESCRIPTION_INSTRUCTION = (
    "Eres un analista de seguridad documentando un pentest. A partir de la EVIDENCIA de la "
    "sesión, redacta una descripción técnica, objetiva y concisa (2-5 frases) de lo que muestra: "
    "qué se hizo y qué se observó. No inventes datos que no estén en la evidencia. En español."
)
_NEXT_STEP_INSTRUCTION = (
    "Eres un analista de seguridad en un pentest. A partir de la EVIDENCIA de la sesión, sugiere "
    "un único siguiente paso razonable y su justificación breve. Básate solo en la evidencia; no "
    "inventes resultados. Escribe en español."
)


TASKS: dict[AISuggestionKind, AITask] = {
    AISuggestionKind.DESCRIPTION: AITask(
        kind=AISuggestionKind.DESCRIPTION,
        prompt_version="description/v1",
        instruction=_DESCRIPTION_INSTRUCTION,
        output_format=(
            "Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional ni formato "
            'markdown, con esta forma exacta: {"description": "<texto>"}.'
        ),
        output_model=DescriptionOutput,
    ),
    AISuggestionKind.NEXT_STEP: AITask(
        kind=AISuggestionKind.NEXT_STEP,
        prompt_version="next_step/v1",
        instruction=_NEXT_STEP_INSTRUCTION,
        output_format=(
            "Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional ni formato "
            'markdown, con esta forma exacta: {"next_step": "<texto>", "rationale": "<texto>"}.'
        ),
        output_model=NextStepOutput,
    ),
}
