"""Mixins reutilizables para los modelos.

Fechas en ``timestamptz`` (ADR-0001 / skill migraciones-postgresql). ``created_at``
y ``updated_at`` tienen ``server_default = now()`` para que el valor lo ponga la
base; ``updated_at`` además se refresca en cada update vía ORM (``onupdate``).
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class CreatedAtMixin:
    """Aporta ``created_at`` (para entidades que solo registran su alta)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class TimestampMixin(CreatedAtMixin):
    """Aporta ``created_at`` + ``updated_at`` (entidades que se editan)."""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
