"""Servicio de las vistas transversales del usuario."""

from uuid import UUID

from app.core.security import effective_project_role
from app.me.repository import MeRepository
from app.me.schemas import MyProjectRead


class MeService:
    """Reglas de las vistas acotadas al usuario."""

    def __init__(self, repository: MeRepository) -> None:
        self._repo = repository

    async def my_projects(self, user_id: UUID) -> list[MyProjectRead]:
        """Lista los proyectos accesibles por el usuario con su rol EFECTIVO (ADR-0002)."""
        rows = await self._repo.list_accessible_projects(user_id)
        result: list[MyProjectRead] = []
        for row in rows:
            effective = effective_project_role(row.workspace_role, row.project_role)
            if effective is None:  # defensivo: el WHERE ya garantiza acceso
                continue
            result.append(
                MyProjectRead(
                    project_id=row.project_id,
                    name=row.name,
                    workspace_id=row.workspace_id,
                    workspace_name=row.workspace_name,
                    role=effective,
                    created_at=row.created_at,
                )
            )
        return result
