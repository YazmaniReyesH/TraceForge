"""Schemas Pydantic de workspaces y de membresías de workspace."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import WorkspaceRole


class WorkspaceCreate(BaseModel):
    """Datos para crear un workspace."""

    name: str = Field(min_length=1, max_length=200)


class WorkspaceRead(BaseModel):
    """Representación pública de un workspace."""

    model_config = ConfigDict(from_attributes=True)

    workspace_id: UUID
    name: str
    created_at: datetime


# ── Membresías de workspace ──


class WorkspaceMemberAdd(BaseModel):
    """Alta de un miembro (usuario existente, por email) con su rol. ``owner`` no se asigna aquí."""

    email: EmailStr
    role: WorkspaceRole


class WorkspaceMemberRoleUpdate(BaseModel):
    """Cambio de rol de un miembro (no a/desde ``owner``: eso es transferencia)."""

    role: WorkspaceRole


class WorkspaceMemberRead(BaseModel):
    """Miembro de un workspace."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email: EmailStr
    display_name: str
    role: WorkspaceRole


class TransferOwnershipRequest(BaseModel):
    """Transferir la propiedad a otro miembro del workspace."""

    new_owner_user_id: UUID
