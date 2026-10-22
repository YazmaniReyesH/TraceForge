"""Repositorio de acceso a ``users`` y ``user_credentials`` (única capa que toca la BD)."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserCredential


class UserRepository:
    """Acceso a datos de identidad y credenciales locales."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_by_email(self, email: str) -> User | None:
        """Busca un usuario por email (ya normalizado)."""
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """Busca un usuario por su id."""
        return await self._session.get(User, user_id)

    async def get_user_and_credential_by_email(
        self, email: str
    ) -> tuple[User, UserCredential] | None:
        """Devuelve (user, credential) de la credencial local para ese email, o ``None``."""
        stmt = (
            select(User, UserCredential)
            .join(UserCredential, UserCredential.user_id == User.user_id)
            .where(User.email == email)
        )
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None
        return row[0], row[1]

    async def flush(self) -> None:
        """Vuelca los INSERT/UPDATE pendientes SIN commit.

        Necesario para respetar el orden de las FKs cuando se insertan entidades
        relacionadas sin ``relationship()`` ORM (el usuario debe existir antes que su
        credencial).
        """
        await self._session.flush()

    def add_user(self, *, email: str, display_name: str) -> User:
        """Agrega un usuario nuevo (id generado en la app). No hace commit."""
        user = User(user_id=uuid4(), email=email, display_name=display_name)
        self._session.add(user)
        return user

    def add_credential(self, *, user_id: UUID, password_hash: str) -> UserCredential:
        """Agrega la credencial local de un usuario. No hace commit."""
        credential = UserCredential(
            user_credential_id=uuid4(),
            user_id=user_id,
            password_hash=password_hash,
        )
        self._session.add(credential)
        return credential
