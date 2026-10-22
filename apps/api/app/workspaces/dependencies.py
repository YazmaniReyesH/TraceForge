"""Dependencias de inyección del módulo de workspaces."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.workspaces.repository import WorkspaceRepository
from app.workspaces.service import WorkspaceService


def get_workspace_repository(
    session: AsyncSession = Depends(get_session),
) -> WorkspaceRepository:
    return WorkspaceRepository(session)


def get_workspace_service(
    repository: WorkspaceRepository = Depends(get_workspace_repository),
    session: AsyncSession = Depends(get_session),
) -> WorkspaceService:
    return WorkspaceService(repository, session)
