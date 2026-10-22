"""Repositorio de usuarios para el invariante de borrado seguro."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProjectMembership, User, WorkspaceMembership


class UserAccountRepository:
    """Acceso a datos de cuentas de usuario (conteo de membresías y borrado)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def count_memberships(self, user_id: UUID) -> int:
        """Total de membresías (workspace + proyecto) del usuario."""
        ws = (
            await self._session.execute(
                select(func.count())
                .select_from(WorkspaceMembership)
                .where(WorkspaceMembership.user_id == user_id)
            )
        ).scalar_one()
        pr = (
            await self._session.execute(
                select(func.count())
                .select_from(ProjectMembership)
                .where(ProjectMembership.user_id == user_id)
            )
        ).scalar_one()
        return int(ws) + int(pr)

    async def delete(self, user: User) -> None:
        await self._session.delete(user)
