"""Implementación Claude del puerto ``AIProvider`` (SDK oficial ``anthropic``).

Detrás del puerto: traduce ``AIPrompt``/``AICompletion`` (dominio) a/desde el SDK. Maneja la
ausencia de API key (``is_configured``), los errores de red/API y el timeout, traducidos a
``AIProviderError`` **sin filtrar secretos** (mensaje genérico; solo el ``code`` llega a la
bitácora). El SDK se importa de forma **perezosa** (dentro del método) para que la app no dependa de
él en tiempo de import y arranque aunque no esté instalado.

Petición mínima de "completar": no se envía ``temperature``/``thinking`` ni se habilitan
herramientas para el modelo (tarea de IA = salida sin herramientas, skill ``backend-fastapi``).
"""

from typing import Any

from app.ai.errors import AINotConfiguredError, AIProviderError
from app.ai.port import AICompletion, AIPrompt, AIProvider
from app.core.config import Settings


class ClaudeProvider(AIProvider):
    """Proveedor de IA sobre el SDK de Anthropic (Claude).

    ``model`` puede sobrescribir el de settings (p. ej. el que resuelve la ``ai_policy`` del
    proyecto; ver ``dependencies.select_provider``). Sin override, se usa ``TF_ANTHROPIC_MODEL``.
    """

    def __init__(self, settings: Settings, *, model: str | None = None) -> None:
        self._settings = settings
        self._model = model or settings.anthropic_model

    @property
    def name(self) -> str:
        return "claude"

    @property
    def model(self) -> str:
        return self._model

    @property
    def is_configured(self) -> bool:
        return bool(self._settings.anthropic_api_key)

    async def complete(self, prompt: AIPrompt, *, max_tokens: int) -> AICompletion:
        if not self.is_configured:
            raise AINotConfiguredError()
        try:
            import anthropic
        except ImportError as exc:  # SDK ausente: error de dominio claro (no rompe el import)
            raise AIProviderError("El SDK de Anthropic no está instalado") from exc

        # Si el prompt trae bloques, se envían como content blocks para activar prompt caching
        # (``cache_control: ephemeral``) en el bloque marcado; si no, texto plano (F1-T3/T4a).
        user_content: Any
        if prompt.user_blocks is not None:
            user_content = [
                {
                    "type": "text",
                    "text": block.text,
                    **({"cache_control": {"type": "ephemeral"}} if block.cache else {}),
                }
                for block in prompt.user_blocks
            ]
        else:
            user_content = prompt.user

        try:
            async with anthropic.AsyncAnthropic(
                api_key=self._settings.anthropic_api_key,
                timeout=self._settings.anthropic_timeout_seconds,
            ) as client:
                message = await client.messages.create(
                    model=self._model,
                    max_tokens=max_tokens,
                    system=prompt.system,
                    messages=[{"role": "user", "content": user_content}],
                )
        except anthropic.APIStatusError as exc:
            # Mensaje seguro (sin cuerpo ni secretos): solo el código de estado.
            raise AIProviderError(f"El proveedor respondió con error {exc.status_code}") from exc
        except anthropic.APIConnectionError as exc:  # incluye timeout (APITimeoutError)
            raise AIProviderError("No se pudo conectar con el proveedor de IA") from exc
        except anthropic.AnthropicError as exc:  # base del SDK, por si acaso
            raise AIProviderError() from exc

        parts: list[str] = []
        for block in message.content:
            block_text = getattr(block, "text", None)
            if isinstance(block_text, str):
                parts.append(block_text)
        return AICompletion(
            text="".join(parts),
            model=message.model,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            stop_reason=message.stop_reason,
        )
