"""Emisión y verificación de JWT de sesión (HS256).

Secreto y caducidad desde settings (``TF_JWT_SECRET`` / ``TF_JWT_EXPIRES_MINUTES``).
El token lleva ``sub`` = ``user_id`` (str). La autorización fina NO va en el token:
el rol y el workspace activo se resuelven en F0-T4b.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import Settings


def create_access_token(subject: str, settings: Settings) -> str:
    """Crea un JWT de acceso para ``subject`` (normalmente el ``user_id``)."""
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=settings.jwt_expires_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    """Decodifica y valida el JWT. Lanza ``jwt.PyJWTError`` si es inválido/expirado."""
    decoded: dict[str, Any] = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    return decoded
