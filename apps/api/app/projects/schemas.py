"""Schemas Pydantic de projects y de membresías de proyecto.

``classification`` y ``ai_policy`` siguen RESERVADOS (ADR-0005): se leen (y ``classification``
se acepta como texto libre), pero no hay lógica de IA ni validación de niveles todavía.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import ProjectRole


class ProjectCreate(BaseModel):
    """Datos para crear un proyecto dentro de un workspace."""

    name: str = Field(min_length=1, max_length=200)
    classification: str | None = Field(default=None, max_length=50)


class ProjectUpdate(BaseModel):
    """Edición parcial de un proyecto (solo los campos presentes)."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    classification: str | None = Field(default=None, max_length=50)


class ProjectRead(BaseModel):
    """Representación pública de un proyecto."""

    model_config = ConfigDict(from_attributes=True)

    project_id: UUID
    workspace_id: UUID
    name: str
    classification: str | None
    ai_policy: dict[str, Any] | None
    created_at: datetime


# ── Membresías de proyecto ──


class ProjectMemberAdd(BaseModel):
    """Alta de un miembro de proyecto (usuario existente, por email) con su rol."""

    email: EmailStr
    role: ProjectRole


class ProjectMemberRoleUpdate(BaseModel):
    """Cambio de rol de un miembro de proyecto."""

    role: ProjectRole


class ProjectMemberRead(BaseModel):
    """Miembro de un proyecto."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email: EmailStr
    display_name: str
    role: ProjectRole
