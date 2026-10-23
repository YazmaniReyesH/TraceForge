"""Convención de errores de TraceForge: envelope ``{code, message}`` (ADR-0009).

Todos los errores de dominio heredan de ``DomainError`` y declaran un ``code`` estable (que el
frontend mapea a i18n) y su ``status_code`` HTTP. Un manejador central los traduce al envelope.
También se normalizan las ``HTTPException`` de Starlette y los errores de validación de entrada.

Statuses: validación de entrada → 422; conflicto de negocio → 409; permiso → 403; no
encontrado/sin acceso → 404; no autenticado → 401.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class DomainError(Exception):
    """Error de dominio con ``code`` estable y ``status_code`` HTTP."""

    code: str = "error"
    status_code: int = 400
    default_message: str = "Ocurrió un error"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


# ── Errores transversales (gate de autorización / sesión) ──


class UnauthenticatedError(DomainError):
    code = "unauthenticated"
    status_code = 401
    default_message = "No autenticado"


class ForbiddenError(DomainError):
    code = "forbidden"
    status_code = 403
    default_message = "No tienes permiso para esta acción"


class NotFoundError(DomainError):
    code = "not_found"
    status_code = 404
    default_message = "No encontrado"


def _envelope(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


_STATUS_CODE = {
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
}


def register_exception_handlers(app: FastAPI) -> None:
    """Registra los manejadores que producen el envelope ``{code, message}``."""

    @app.exception_handler(DomainError)
    async def _handle_domain(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_envelope(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_envelope("validation_error", "Los datos enviados no son válidos"),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _STATUS_CODE.get(exc.status_code, "http_error")
        message = exc.detail if isinstance(exc.detail, str) else code
        headers = getattr(exc, "headers", None)
        return JSONResponse(
            status_code=exc.status_code, content=_envelope(code, message), headers=headers
        )
