"""Implementación local del puerto ``AuthProvider`` (email + contraseña)."""

from app.auth.errors import EmailAlreadyRegisteredError
from app.auth.hashing import Argon2Hasher
from app.auth.port import AuthProvider
from app.auth.repository import UserRepository
from app.models import User


class LocalAuthProvider(AuthProvider):
    """Autenticación con credencial local (contraseña hasheada con argon2id)."""

    def __init__(self, repository: UserRepository, hasher: Argon2Hasher) -> None:
        self._repo = repository
        self._hasher = hasher

    async def register(self, *, email: str, password: str, display_name: str) -> User:
        """Crea usuario + credencial local. El commit lo hace el servicio."""
        if await self._repo.get_user_by_email(email) is not None:
            raise EmailAlreadyRegisteredError
        user = self._repo.add_user(email=email, display_name=display_name)
        # El usuario debe estar insertado ANTES que su credencial (FK user_credentials ->
        # users). Sin relationship() ORM, forzamos el orden con un flush explícito.
        await self._repo.flush()
        self._repo.add_credential(user_id=user.user_id, password_hash=self._hasher.hash(password))
        return user

    async def authenticate(self, *, email: str, password: str) -> User | None:
        """Verifica credenciales. Mismo coste de tiempo exista o no el usuario."""
        found = await self._repo.get_user_and_credential_by_email(email)
        if found is None:
            # Verificación señuelo: iguala tiempos y evita enumeración por temporización.
            self._hasher.dummy_verify()
            return None
        user, credential = found
        if not self._hasher.verify(credential.password_hash, password):
            return None
        return user
