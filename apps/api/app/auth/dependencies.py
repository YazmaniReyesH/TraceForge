"""Dependencias FastAPI de autenticación (inyección de capas y ``get_current_user``)."""

from functools import lru_cache
from uuid import UUID

import jwt
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.hashing import Argon2Hasher
from app.auth.local_provider import LocalAuthProvider
from app.auth.port import AuthProvider
from app.auth.repository import UserRepository
from app.auth.service import AuthService
from app.auth.tokens import decode_access_token
from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.core.errors import UnauthenticatedError
from app.models import User


@lru_cache
def _build_hasher() -> Argon2Hasher:
    # Singleton: argon2 precalcula un hash señuelo; no conviene repetirlo por request.
    return Argon2Hasher(get_settings())


def get_password_hasher() -> Argon2Hasher:
    """Hasher argon2id compartido."""
    return _build_hasher()


def get_user_repository(session: AsyncSession = Depends(get_session)) -> UserRepository:
    """Repositorio de usuarios/credenciales ligado a la sesión del request."""
    return UserRepository(session)


def get_auth_provider(
    repository: UserRepository = Depends(get_user_repository),
    hasher: Argon2Hasher = Depends(get_password_hasher),
) -> AuthProvider:
    """Proveedor de autenticación (hoy, el local)."""
    return LocalAuthProvider(repository, hasher)


def get_auth_service(
    provider: AuthProvider = Depends(get_auth_provider),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    """Servicio de autenticación."""
    return AuthService(provider, session, settings)


def _extract_token(request: Request, cookie_name: str) -> str | None:
    """Toma el token de ``Authorization: Bearer`` o, si no, de la cookie de sesión."""
    header = request.headers.get("Authorization")
    if header and header.lower().startswith("bearer "):
        return header[len("bearer ") :].strip()
    return request.cookies.get(cookie_name)


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> User:
    """Resuelve el usuario autenticado desde el token. 401 si falta o es inválido.

    NO resuelve workspace activo ni rol (eso es F0-T4b).
    """
    token = _extract_token(request, settings.auth_cookie_name)
    if not token:
        raise UnauthenticatedError()

    try:
        payload = decode_access_token(token, settings)
    except jwt.PyJWTError as exc:
        raise UnauthenticatedError() from exc

    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise UnauthenticatedError()
    try:
        user_id = UUID(subject)
    except ValueError as exc:
        raise UnauthenticatedError() from exc

    user = await UserRepository(session).get_user_by_id(user_id)
    if user is None:
        raise UnauthenticatedError()
    return user
