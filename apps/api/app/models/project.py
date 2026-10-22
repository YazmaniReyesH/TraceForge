"""Entidad ``projects`` — unidad de trabajo dentro de un workspace (ADR-0002)."""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin


class Project(TimestampMixin, Base):
    """Un pentest, auditoría, BCP, etc. Pertenece a un único workspace."""

    __tablename__ = "projects"

    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Aislamiento: todo proyecto pertenece a un workspace (NOT NULL + índice).
    # ON DELETE CASCADE: borrar un workspace arrastra sus proyectos (ver ADR-0006).
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # RESERVADO: clasificación del proyecto (niveles TBD en F1). Sin CHECK todavía.
    classification: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # RESERVADO (ADR-0005): política de IA por proyecto. Sin uso en código aún.
    ai_policy: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
