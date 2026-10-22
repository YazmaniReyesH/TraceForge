"""Entidad ``workspaces`` — el inquilino (tenant) y unidad de aislamiento (ADR-0002)."""

import uuid
from typing import Any

from sqlalchemy import String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin


class Workspace(TimestampMixin, Base):
    """Inquilino: tope de la jerarquía y frontera de aislamiento."""

    __tablename__ = "workspaces"

    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # RESERVADO (ADR-0005): "techo" de política de IA del workspace. Sin uso en
    # código todavía; su aplicación efectiva es de F1. Nullable a propósito.
    ai_policy: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
