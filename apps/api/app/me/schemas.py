"""Schemas de las vistas transversales del usuario."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import ProjectRole


class MyProjectRead(BaseModel):
    """Un proyecto accesible por el usuario, con el contexto de su workspace y su rol efectivo."""

    project_id: UUID
    name: str
    workspace_id: UUID
    workspace_name: str
    role: ProjectRole  # rol EFECTIVO del usuario sobre el proyecto (ADR-0002)
    created_at: datetime
