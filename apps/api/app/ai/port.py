"""Puerto de dominio ``AIProvider`` (patrón port/adapter, ADR-0003/0004/0005).

Abstrae *cómo* se completa un prompt con un proveedor de IA en la nube, en términos del **dominio**
(no del SDK de un proveedor concreto). Hoy existe la implementación Claude (``claude_provider.py``);
**OpenAI/Gemini serían otras implementaciones de esta misma interfaz** (F4), sin tocar el servicio
ni los endpoints — el mismo patrón port/adapter que ``AuthProvider`` (ADR-0007) y que el storage.

El servicio **arma el prompt** (evidencia ya redactada y delimitada como dato no confiable) y se lo
pasa al puerto; el puerto solo llama al proveedor y **normaliza** la respuesta a tipos del dominio.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AIPrompt:
    """Prompt estructurado, independiente del proveedor.

    ``system``: instrucciones de sistema (rol + reglas anti-inyección).
    ``user``: mensaje del usuario con la evidencia ya **redactada** y **delimitada**.
    """

    system: str
    user: str


@dataclass(frozen=True)
class AICompletion:
    """Resultado normalizado de una completación: texto + metadatos de procedencia (ADR-0003)."""

    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    stop_reason: str | None = None


class AIProvider(ABC):
    """Puerto: identidad del proveedor, si está configurado, y una operación de completar."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Identificador estable del proveedor (p. ej. ``"claude"``), para la bitácora."""
        ...

    @property
    @abstractmethod
    def model(self) -> str:
        """Modelo que usaría esta instancia (leído de settings)."""
        ...

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """True si hay credenciales para llamar al proveedor; si no, el servicio degrada."""
        ...

    @abstractmethod
    async def complete(self, prompt: AIPrompt, *, max_tokens: int) -> AICompletion:
        """Completa el prompt. Lanza ``AINotConfiguredError``/``AIProviderError`` (sin secretos)."""
        ...
