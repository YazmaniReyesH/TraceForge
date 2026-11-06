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


class AIInvalidOutputError(AIError):
    # La salida del modelo no cumple el JSON Schema esperado (ADR-0004: el código valida la forma).
    code = "ai_invalid_output"
    status_code = 502
    default_message = "La IA devolvió una respuesta con una forma inválida"


class AINoEvidenceError(AIError):
    # No hay evidencia activa en la sesión sobre la cual trabajar (generar o analizar).
    code = "ai_no_evidence"
    status_code = 409
    default_message = "La sesión no tiene evidencia activa sobre la cual trabajar"


class AINoAnalysisError(AIError):
    # Todavía no se ha generado un análisis para esta sesión (GET del último sin llamar a la API).
    code = "ai_no_analysis"
    status_code = 404
    default_message = "La sesión aún no tiene un análisis de contexto"


class AISuggestionInvalidTransitionError(AIError):
    # Transición de estado no permitida (p. ej. aceptar una ya aceptada).
    code = "ai_suggestion_invalid_transition"
    status_code = 409
    default_message = "La sugerencia no admite esta transición de estado"
