"""Router de autenticación. Delgado: valida entrada, delega al servicio, traduce errores.

Transporte del token: **cookie httpOnly** (ver ADR-0007). El login la emite; el logout
la borra; ``get_current_user`` también acepta ``Authorization: Bearer`` (útil para
clientes de API y pruebas).
"""

from typing import Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.auth.dependencies import get_auth_service, get_current_user
from app.auth.errors import EmailAlreadyRegisteredError, InvalidCredentialsError
from app.auth.schemas import LoginRequest, RegisterRequest, UserRead
from app.auth.service import AuthService
from app.core.config import Settings, get_settings
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
    """Registra un usuario nuevo. Error genérico si no se pudo (no confirma el email)."""
    try:
        return await service.register(
            email=data.email, password=data.password, display_name=data.display_name
        )
    except EmailAlreadyRegisteredError as exc:
        # Mensaje deliberadamente genérico para no facilitar enumeración de usuarios.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo completar el registro",
        ) from exc


@router.post("/login", response_model=UserRead)
async def login(
    data: LoginRequest,
    response: Response,
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> User:
    """Inicia sesión: emite la cookie de sesión. 401 genérico si fallan las credenciales."""
    try:
        user, token = await service.login(email=data.email, password=data.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        ) from exc
    _set_session_cookie(response, token, settings)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    settings: Settings = Depends(get_settings),
) -> None:
    """Cierra sesión borrando la cookie. Idempotente (no exige token válido)."""
    response.delete_cookie(key=settings.auth_cookie_name, path="/")


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)) -> User:
    """Devuelve el usuario autenticado (401 si no hay sesión válida)."""
    return user
