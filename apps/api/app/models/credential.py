"""Entidad ``user_credentials`` — credencial local (email + contraseña) (F0-T4a).

Las credenciales viven en una tabla APARTE (no en ``users``) para aislar los
secretos de la identidad y poder sumar otros métodos de login a futuro (SSO) detrás
del puerto ``AuthProvider`` sin tocar ``users`` (ver ADR-0007). Esta tabla guarda la
credencial de contraseña local: una por usuario (``UNIQUE user_id``). El hash NUNCA
se expone en schemas de respuesta.
"""

import uuid

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin


class UserCredential(TimestampMixin, Base):
    """Credencial local (password) de un usuario."""

    __tablename__ = "user_credentials"

    user_credential_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    # Una credencial local por usuario. ON DELETE CASCADE: borrar el usuario borra su
    # credencial (la credencial no tiene sentido sin su usuario). Ver ADR-0007.
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # Hash de la contraseña (argon2id). NUNCA en claro, NUNCA en logs ni en schemas.
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
