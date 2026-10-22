"""Patrón base de repository con **filtro por workspace** (aislamiento multi-tenant).

Los recursos que pertenecen a un workspace (projects y, más adelante, evidencia,
hallazgos, documentos…) deben consultarse SIEMPRE acotados al workspace del contexto.
Para que el aislamiento no dependa de recordar el ``WHERE`` en cada query, los repos de
esos recursos heredan de ``WorkspaceScopedRepository`` y construyen sus lecturas desde
``scoped_select()``, que ya impone ``WHERE workspace_id = <contexto>``.

Uso (F0-T4b-2), p. ej. para projects::

    class ProjectRepository(WorkspaceScopedRepository):
        model = Project

        async def list(self) -> Sequence[Project]:
            return (await self._session.execute(self.scoped_select())).scalars().all()

El ``workspace_id`` proviene del ``WorkspaceContext`` (resuelto y verificado por la capa de
autorización), nunca del cliente directamente.
"""

from typing import Any, ClassVar
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession


class WorkspaceScopedRepository:
    """Base para repositories de recursos pertenecientes a un workspace."""

    #: Modelo SQLAlchemy del recurso; DEBE tener una columna ``workspace_id``.
    model: ClassVar[type[Any]]

    def __init__(self, session: AsyncSession, workspace_id: UUID) -> None:
        self._session = session
        self._workspace_id = workspace_id

    def scoped_select(self) -> Select[Any]:
        """``select(model)`` ya filtrado por el workspace del contexto."""
        return select(self.model).where(self.model.workspace_id == self._workspace_id)
