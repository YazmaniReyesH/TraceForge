"""Entidad ``sessions`` — línea de tiempo dentro de un proyecto (F1).

Un project tiene 0..N sessions; cada sesión agrupa ítems de evidencia en orden cronológico.
Aislamiento: cuelga del project (y por tanto del workspace). Soft-delete con ``deleted_at``.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin


class Session(TimestampMixin, Base):
    """Una línea de tiempo (sesión) de un proyecto."""

    __tablename__ = "sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # ON DELETE CASCADE: borrar el project arrastra sus sesiones (ver ADR-0006).
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Soft-delete (cadena de custodia): nunca se borra físicamente (ver ADR-0012).
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
