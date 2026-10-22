"""Servicio de autenticación: orquesta normalización, provider y emisión de token.

No conoce HTTP. Normaliza el email (minúsculas + trim) ANTES de registrar/buscar,
cerrando la nota de F0-T3b (el UNIQUE de BD es sensible a mayúsculas; normalizar en el
servicio mantiene una sola forma canónica). El commit de la unidad de trabajo vive aquí.
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.errors import EmailAlreadyRegisteredError, InvalidCredentialsError
from app.auth.port import AuthProvider
from app.auth.tokens import create_access_token
from app.core.config import Settings
from app.models import User


class AuthService:
    """Reglas de negocio de registro e inicio de sesión."""

    def __init__(self, provider: AuthProvider, session: AsyncSession, settings: Settings) -> None:
        self._provider = provider
        self._session = session
        self._settings = settings

    @staticmethod
    def normalize_email(email: str) -> str:
        """Forma canónica del email: sin espacios y en minúsculas."""
        return email.strip().lower()

    async def register(self, *, email: str, password: str, display_name: str) -> User:
        """Registra un usuario. Lanza ``EmailAlreadyRegistered`` si el email ya existe."""
        normalized = self.normalize_email(email)
        try:
            user = await self._provider.register(
                email=normalized, password=password, display_name=display_name.strip()
            )
            await self._session.commit()
        except EmailAlreadyRegisteredError:
            await self._session.rollback()
            raise
        except IntegrityError as exc:
            # Carrera: otro registro ganó el UNIQUE entre el chequeo y el commit.
            await self._session.rollback()
            raise EmailAlreadyRegisteredError from exc
        return user

    async def login(self, *, email: str, password: str) -> tuple[User, str]:
        """Valida credenciales y devuelve (user, token). Lanza ``InvalidCredentials``."""
        normalized = self.normalize_email(email)
        user = await self._provider.authenticate(email=normalized, password=password)
        if user is None:
            raise InvalidCredentialsError
        token = create_access_token(str(user.user_id), self._settings)
        return user, token
