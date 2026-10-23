"""Protección CSRF con patrón **double-submit token** (ADR-0010).

La sesión viaja en una cookie httpOnly (no accesible desde JS), así que un sitio atacante no la
puede leer, pero el navegador sí la envía en peticiones cross-site → riesgo CSRF. El patrón
double-submit añade una cookie **legible** ``tf_csrf`` y exige que cada mutación repita su valor
en el header ``X-CSRF-Token``. Un atacante no puede leer la cookie (same-origin policy) para
replicarla en el header, así que la mutación falla.

- Los métodos seguros (GET/HEAD/OPTIONS) **nunca** mutan y no se validan.
- ``require_csrf`` se aplica a nivel de router en los recursos que mutan estado.
"""

import secrets

from fastapi import Depends, Request
from fastapi import Response as FastAPIResponse

from app.core.config import Settings, get_settings
from app.core.errors import DomainError

CSRF_HEADER = "X-CSRF-Token"
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class CsrfError(DomainError):
    code = "csrf_failed"
    status_code = 403
    default_message = "Token CSRF ausente o inválido"


def generate_csrf_token() -> str:
    """Genera un token CSRF aleatorio."""
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response: FastAPIResponse, token: str, settings: Settings) -> None:
    """Emite la cookie CSRF (NO httpOnly: el frontend debe poder leerla)."""
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=token,
        max_age=settings.jwt_expires_minutes * 60,
        httponly=False,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )


def require_csrf(request: Request, settings: Settings = Depends(get_settings)) -> None:
    """Exige ``X-CSRF-Token`` == cookie CSRF en mutaciones **con sesión**.

    Si no hay cookie de sesión no hay nada que un CSRF pueda reenviar, y se deja pasar para que
    la autenticación responda 401 (en vez de un 403 CSRF confuso). Con sesión presente —el caso
    que un ataque CSRF explotaría— la validación es obligatoria.
    """
    if request.method in _SAFE_METHODS:
        return
    if settings.auth_cookie_name not in request.cookies:
        return
    cookie = request.cookies.get(settings.csrf_cookie_name)
    header = request.headers.get(CSRF_HEADER)
    if not cookie or not header or not secrets.compare_digest(cookie, header):
        raise CsrfError()
