"""Hashing de contraseñas con **argon2id** (argon2-cffi).

Argon2id es la primera recomendación de OWASP (memory-hard) y evita el límite de 72
bytes de bcrypt. Factor de costo configurable vía settings. La contraseña NUNCA se
guarda en claro ni se registra en logs.
"""

import contextlib

from argon2 import PasswordHasher
from argon2.exceptions import (
    HashingError,
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

from app.core.config import Settings

# Contraseña ficticia para igualar el tiempo de verificación cuando el usuario no
# existe (mitiga enumeración por temporización). Nunca es una credencial válida.
_DUMMY_PASSWORD = "tf-dummy-password-not-used"


class Argon2Hasher:
    """Envoltura de ``argon2.PasswordHasher`` con parámetros desde settings."""

    def __init__(self, settings: Settings) -> None:
        self._ph = PasswordHasher(
            time_cost=settings.argon2_time_cost,
            memory_cost=settings.argon2_memory_cost,
            parallelism=settings.argon2_parallelism,
        )
        # Se precalcula una vez (argon2 es caro) para `dummy_verify`.
        self._dummy_hash = self._ph.hash(_DUMMY_PASSWORD)

    def hash(self, password: str) -> str:
        """Devuelve el hash argon2id de la contraseña."""
        return self._ph.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        """True si la contraseña coincide con el hash; False si no."""
        try:
            self._ph.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError, HashingError):
            return False
        return True

    def dummy_verify(self) -> None:
        """Verificación señuelo para igualar tiempos cuando el usuario no existe."""
        with contextlib.suppress(
            VerifyMismatchError, VerificationError, InvalidHashError, HashingError
        ):
            self._ph.verify(self._dummy_hash, "wrong-password")
