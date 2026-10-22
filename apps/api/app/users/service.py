"""Servicio de usuarios: borrado seguro (invariante). Sin endpoint de baja en esta fase."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.users.errors import UserHasMembershipsError, UserNotFoundError
from app.users.repository import UserAccountRepository


class UserService:
    """Reglas de negocio de cuentas de usuario."""

    def __init__(self, repository: UserAccountRepository, session: AsyncSession) -> None:
        self._repo = repository
        self._session = session

    async def delete_user(self, user_id: UUID) -> None:
        """Borra un usuario SOLO si no tiene membresías.

        Respeta el ``ON DELETE RESTRICT`` de las membresías (ADR-0006) con un error de dominio
        claro en vez de dejar que explote la FK. El flujo completo de baja (revocar membresías,
        transferir titularidades) queda para otra fase. [[POR LLENAR: endpoint y flujo de baja]].
        """
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError
        if await self._repo.count_memberships(user_id) > 0:
            raise UserHasMembershipsError
        await self._repo.delete(user)
        await self._session.commit()
