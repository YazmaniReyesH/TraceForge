"""Capa de redacción de secretos (ADR-0005): DETERMINISTA, NO IA.

Antes de que cualquier contenido cruce el perímetro hacia un proveedor en la nube, esta capa
reemplaza los secretos por **marcadores estables**: dentro de UN mismo texto, el mismo secreto
produce siempre el mismo marcador (``[REDACTED_<TIPO>_<n>]``). Devuelve el texto redactado, el
**mapa marcador→valor** (en memoria; en F1-T3 NO se persiste — eso es F1-T4, cifrado) y cuántos
secretos se enmascararon.

Qué se redacta (alto riesgo, SIEMPRE — ADR-0005):

| Tipo (marcador)          | Qué cubre (resumen)                                     |
|--------------------------|---------------------------------------------------------|
| PRIVATE_KEY              | Bloque PEM ``BEGIN … PRIVATE KEY … END`` (completo)     |
| JWT                      | Token JWT (``eyJ…`` . … . …)                             |
| AWS_KEY                  | AWS Access Key ID (``AKIA…``)                           |
| API_KEY                  | Claves ``sk-``/``pk-``/``rk-`` (OpenAI/Anthropic/Stripe)|
| TOKEN                    | Token tras ``Bearer `` (conserva "Bearer ")            |
| SECRET                   | Valor de ``api_key/secret/token/access_key/auth = …``   |
| PASSWORD                 | Valor de ``password/passwd/pwd = …``                    |
| HASH                     | Hash hex: sha256 (64) / sha1 (40) / md5 (32)            |

**Qué NO se redacta (por ahora):** PII e IPs quedan fuera por defecto (dependen de la
política/clasificación del proyecto, aún reservada en ``projects.ai_policy``; se añadirán cuando
esa política se implemente, F1-T4+). Tampoco se toca texto que no case ningún patrón.

**Equilibrio (importante):** la redacción **preserva la estructura** que el modelo necesita
entender: en una asignación se enmascara SOLO el valor y se conserva la clave
(``password=[REDACTED_PASSWORD_1]``), y ``Bearer``/el encabezado PEM se conservan como pistas de
forma. Así el modelo sigue "entendiendo" que había una contraseña/clave sin ver su valor.

**Relación con el realce semántico del frontend** (``modules/timeline/components/semantic.ts``):
comparten la *forma* del patrón de hash (hex por longitud), pero **no se acoplan**. Son cosas
distintas y con objetivos opuestos (esta capa OCULTA en el backend antes de salir a la nube;
aquella COLOREA en el navegador) y viven en lenguajes distintos (Python vs TypeScript). Acoplarlas
obligaría a compartir un origen entre dos capas con metas opuestas; duplicar un patrón pequeño es
más seguro.

``[[POR LLENAR: la redacción determinista nunca es perfecta ante datos arbitrarios; el catálogo de
patrones debe revisarse y ampliarse, y la redacción de PII/IPs por clasificación se definirá con la
política de IA por proyecto (ADR-0005).]]``
"""

import re
from dataclasses import dataclass, field

# Marcador ya insertado: se usa para NO volver a redactar un marcador (p. ej. ``token=sk-…`` donde
# ``sk-…`` ya fue enmascarado por API_KEY antes de que corra el patrón SECRET).
_MARKER_RE = re.compile(r"\[REDACTED_[A-Z_]+_\d+\]")


@dataclass
class RedactionResult:
    """Texto redactado + mapa marcador→valor real (en memoria) + conteo de secretos."""

    text: str
    mapping: dict[str, str] = field(default_factory=dict)
    count: int = 0


# Cada patrón: (tipo, regex, grupo_a_redactar). grupo 0 = toda la coincidencia; >0 = solo ese grupo
# (preserva la estructura). El ORDEN importa: específico → genérico, para que un secreto no lo
# capture un patrón más amplio.
_IPV_SECRET = (
    r"(?i)\b(api[_-]?key|secret|token|access[_-]?key|auth[_-]?token)\b\s*[:=]\s*[\"']?([^\s\"']+)"
)
_ASSIGN_PASSWORD = r"(?i)\b(password|passwd|pwd)\b\s*[:=]\s*[\"']?([^\s\"']+)"

_PATTERNS: list[tuple[str, re.Pattern[str], int]] = [
    (
        "PRIVATE_KEY",
        re.compile(
            r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
        0,
    ),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"), 0),
    ("AWS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), 0),
    ("API_KEY", re.compile(r"\b(?:sk|pk|rk)-[A-Za-z0-9_-]{16,}\b"), 0),
    ("TOKEN", re.compile(r"\b(Bearer)\s+([A-Za-z0-9._-]{8,})", re.IGNORECASE), 2),
    ("SECRET", re.compile(_IPV_SECRET), 2),
    ("PASSWORD", re.compile(_ASSIGN_PASSWORD), 2),
    ("HASH", re.compile(r"\b[0-9a-fA-F]{64}\b|\b[0-9a-fA-F]{40}\b|\b[0-9a-fA-F]{32}\b"), 0),
]


def _sub_pattern(
    text: str,
    label: str,
    pattern: re.Pattern[str],
    group: int,
    value_to_marker: dict[tuple[str, str], str],
    counters: dict[str, int],
    mapping: dict[str, str],
) -> str:
    """Aplica un patrón, reemplazando el ``group`` por un marcador estable (helper sin B023)."""

    def _replace(match: re.Match[str]) -> str:
        value = match.group(group)
        if not value or _MARKER_RE.fullmatch(value):
            return match.group(0)  # nada que redactar / ya es un marcador
        key = (label, value)
        marker = value_to_marker.get(key)
        if marker is None:
            counters[label] = counters.get(label, 0) + 1
            marker = f"[REDACTED_{label}_{counters[label]}]"
            value_to_marker[key] = marker
            mapping[marker] = value
        if group == 0:
            return marker
        # Preserva lo anterior/posterior al grupo (clave, "Bearer ", comillas…).
        whole = match.group(0)
        rel_start = match.start(group) - match.start(0)
        rel_end = match.end(group) - match.start(0)
        return whole[:rel_start] + marker + whole[rel_end:]

    return pattern.sub(_replace, text)


def redact(text: str) -> RedactionResult:
    """Redacta los secretos de ``text`` con marcadores estables. No muta la entrada."""
    if not text:
        return RedactionResult(text=text)
    value_to_marker: dict[tuple[str, str], str] = {}
    counters: dict[str, int] = {}
    mapping: dict[str, str] = {}
    result = text
    for label, pattern, group in _PATTERNS:
        result = _sub_pattern(result, label, pattern, group, value_to_marker, counters, mapping)
    return RedactionResult(text=result, mapping=mapping, count=len(mapping))
