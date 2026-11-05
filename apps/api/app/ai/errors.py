"""Errores de dominio del gateway de IA (envelope {code, message} vía DomainError, ADR-0009).

Los mensajes de estos errores NUNCA deben contener secretos ni la API key: el proveedor se traduce
a un error de dominio con un ``code`` estable y un mensaje genérico seguro.
"""

from app.core.errors import DomainError


class AIError(DomainError):
    """Base de los errores del gateway de IA."""


class AINotConfiguredError(AIError):
    code = "ai_not_configured"
    status_code = 503
    default_message = "La IA no está configurada (falta la API key del proveedor)"


class AIProviderError(AIError):
    code = "ai_provider_error"
    status_code = 502
    default_message = "El proveedor de IA no pudo completar la solicitud"
