"""Entidad ``users`` — identidad global a la instancia (ADR-0002).

La identidad es global: un mismo usuario puede pertenecer a varios workspaces con
rol distinto en cada uno (las membresías viven en otras tablas). La autenticación
(password/SSO) llega en F0-T4; aquí solo la identidad.
"""

import uuid

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin


class User(TimestampMixin, Base):
    """Persona que se autentica en TraceForge."""

    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Único en TODA la instancia. La normalización (p. ej. a minúsculas) es
    # responsabilidad del servicio en F0-T4; aquí el unique es sobre el valor guardado.
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
