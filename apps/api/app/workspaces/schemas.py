"""Schemas Pydantic de workspaces."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceCreate(BaseModel):
    """Datos para crear un workspace."""

    name: str = Field(min_length=1, max_length=200)


class WorkspaceRead(BaseModel):
    """Representación pública de un workspace."""

    model_config = ConfigDict(from_attributes=True)

    workspace_id: UUID
    name: str
    created_at: datetime
