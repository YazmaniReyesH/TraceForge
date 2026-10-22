"""Dependencias de inyección del módulo de projects."""

from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.projects.repository import ProjectRepository
from app.projects.service import ProjectService


def get_project_repository(
    workspace_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ProjectRepository:
    # El workspace_id viene de la ruta; el repository queda acotado a ese workspace.
    return ProjectRepository(session, workspace_id)


def get_project_service(
    repository: ProjectRepository = Depends(get_project_repository),
    session: AsyncSession = Depends(get_session),
) -> ProjectService:
    return ProjectService(repository, session)
