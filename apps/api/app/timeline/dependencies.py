"""Dependencias de inyección del timeline (usa el contexto de proyecto ya resuelto)."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import ProjectContext, get_project_context
from app.timeline.repository import TimelineRepository
from app.timeline.service import TimelineService


def get_timeline_service(
    context: ProjectContext = Depends(get_project_context),
    session: AsyncSession = Depends(get_session),
) -> TimelineService:
    # project_id y user salen del contexto de proyecto (gate ya aplicado en el router).
    repository = TimelineRepository(session, context.project_id)
    return TimelineService(repository, session, context.user.user_id)
