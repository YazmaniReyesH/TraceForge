"""Schemas Pydantic de autenticación. ``UserRead`` NUNCA incluye el hash."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Datos para registrar un usuario nuevo."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    """Credenciales de inicio de sesión."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    """Representación pública del usuario (sin credenciales)."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email: EmailStr
    display_name: str
    created_at: datetime
