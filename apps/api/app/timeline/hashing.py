"""Cálculo del ``content_hash`` de una versión de evidencia (cadena de custodia, ADR-0012).

El hash es **SHA-256** sobre los **bytes UTF-8** de un **JSON canónico** del CONTENIDO de la
evidencia (no de su presentación). Canónico = ``json.dumps(obj, sort_keys=True, ensure_ascii=False,
separators=(",", ":"))`` — claves ordenadas y sin espacios, para que sea reproducible y verificable.

Forma del objeto canónico:
- command: ``{"kind": "command", "command": <command_text>, "output": <command_output>}``
- note:    ``{"kind": "note", "text": <note_text>}``

Los campos ausentes se normalizan a cadena vacía. ``tool`` y ``language`` son pistas de
presentación y **NO** entran en el hash (no forman parte de la evidencia). Un mismo contenido
produce siempre el mismo hash; cualquier verificador puede recomputarlo con esta misma regla.
"""

import hashlib
import json

from app.models.enums import EvidenceKind


def compute_content_hash(
    kind: EvidenceKind,
    *,
    command_text: str | None = None,
    command_output: str | None = None,
    note_text: str | None = None,
) -> str:
    """Devuelve el SHA-256 (hex) del contenido canónico de la evidencia."""
    if kind == EvidenceKind.COMMAND:
        canonical: dict[str, str] = {
            "kind": "command",
            "command": command_text or "",
            "output": command_output or "",
        }
    else:
        canonical = {"kind": "note", "text": note_text or ""}
    payload = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
