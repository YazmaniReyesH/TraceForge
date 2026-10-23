"""Router de autenticación. Delgado: valida entrada, delega al servicio.

Transporte de sesión: **cookie httpOnly** (ADR-0007). CSRF double-submit (ADR-0010): login y
``/me`` emiten también la cookie legible ``tf_csrf``; las mutaciones exigen ``X-CSRF-Token``.
Los errores de dominio se traducen al envelope ``{code, message}`` por el manejador central.
"""

from typing import Literal, cast

from fastapi import APIRouter, Depends, Response, status

from app.auth.dependencies import get_auth_service, get_current_user
from app.auth.schemas import LoginRequest, RegisterRequest, UserRead
from app.auth.service import AuthService
from app.core.config import Settings, get_settings
from app.core.csrf import generate_csrf_token, require_csrf, set_csrf_cookie
from app.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.jwt_expires_minutes * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=cast(Literal["lax", "strict", "none"], settings.auth_cookie_samesite),
        path="/",
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> User:
    """Registra un usuario nuevo (sin CSRF: es un flujo de arranque, pre-sesión)."""
    return await service.register(
        email=data.email, password=data.password, display_name=data.display_name
    )


@router.post("/login", response_model=UserRead)
async def login(
    data: LoginRequest,
    response: Response,
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> User:
    """Inicia sesión: emite la cookie de sesión y la cookie CSRF. 401 si credenciales inválidas."""
    user, token = await service.login(email=data.email, password=data.password)
    _set_session_cookie(response, token, settings)
    set_csrf_cookie(response, generate_csrf_token(), settings)
    return user


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def logout(
    response: Response,
    settings: Settings = Depends(get_settings),
) -> None:
    """Cierra sesión borrando ambas cookies. Exige CSRF (es una mutación)."""
    response.delete_cookie(key=settings.auth_cookie_name, path="/")
    response.delete_cookie(key=settings.csrf_cookie_name, path="/")


@router.get("/me", response_model=UserRead)
async def me(
    response: Response,
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> User:
    """Devuelve el usuario autenticado y refresca la cookie CSRF (para hidratar la sesión)."""
    set_csrf_cookie(response, generate_csrf_token(), settings)
    return user


@router.get("/csrf", status_code=status.HTTP_204_NO_CONTENT)
async def issue_csrf(
    response: Response,
    settings: Settings = Depends(get_settings),
) -> None:
    """Emite (o renueva) la cookie CSRF. Útil para obtener un token antes de una mutación."""
    set_csrf_cookie(response, generate_csrf_token(), settings)
