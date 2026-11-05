"""Entidades de evidencia del timeline (F1): ítem lógico + versiones inmutables.

Cadena de custodia (ADR-0012): la evidencia es **append-only**. El ítem lógico
(``evidence_items``) guarda metadatos mutables de bookkeeping (posición, puntero a la versión
actual, soft-delete); el CONTENIDO vive en filas **inmutables** de ``evidence_item_versions``
(nunca se hace UPDATE sobre ellas). "Editar" = insertar una versión nueva; "borrar" = soft-delete
del ítem lógico. Cada versión lleva su ``content_hash`` (SHA-256) y su ``captured_at``.

Reservas (no modeladas aún): el contenido generado por IA (ADR-0003, con procedencia/estado) y los
hallazgos futuros colgarán de ``session_id`` / ``evidence_item_id`` en tablas propias; la PK estable
del ítem deja la puerta abierta sin acoplar nada ahora.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import EvidenceKind, sql_in_clause
from app.models.mixins import CreatedAtMixin, TimestampMixin
from app.models.types import StrEnumType


class EvidenceItem(TimestampMixin, Base):
    """Ítem lógico de evidencia (una posición del timeline). Su contenido vive en versiones."""

    __tablename__ = "evidence_items"

    evidence_item_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # ON DELETE CASCADE: borrar la sesión arrastra sus ítems (ver ADR-0006).
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[EvidenceKind] = mapped_column(StrEnumType(EvidenceKind, length=20), nullable=False)
    # Orden dentro de la sesión en **escala con huecos** (múltiplos de ~1000; ver ADR-0013).
    # Permite insertar/reordenar "entre dos" tomando un valor intermedio sin renumerar todo.
    # NO es único: el orden se desempata determinísticamente por (position, created_at, id).
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    # Puntero a la versión vigente (bookkeeping; el contenido es inmutable en las versiones).
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Soft-delete: nunca se borra físicamente (cadena de custodia).
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            f"kind IN ({sql_in_clause(EvidenceKind)})",
            name="ck_evidence_items_kind",
        ),
        # Índice de orden del timeline, **no único** (ADR-0013): cubre el filtro por session_id
        # (columna líder) y acelera el ORDER BY (session_id, position). La no-unicidad evita
        # colisiones transitorias al renumerar o reordenar de forma optimista.
        Index("ix_evidence_items_session_position", "session_id", "position"),
    )


class EvidenceItemVersion(CreatedAtMixin, Base):
    """Versión INMUTABLE del contenido de un ítem de evidencia (nunca se hace UPDATE)."""

    __tablename__ = "evidence_item_versions"

    evidence_item_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    evidence_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_items.evidence_item_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    # SHA-256 (hex, 64 chars) del contenido canónico (ver service.compute_content_hash / ADR-0012).
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Momento de captura de ESTA versión (puede diferir de created_at).
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Contenido (texto). Según kind: command -> command_text/command_output; note -> note_text.
    command_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    command_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Pistas de presentación (RESERVADO para la UI de F1-T2): NO entran en el content_hash.
    tool: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    note_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("evidence_item_id", "version", name="uq_evidence_item_versions_item_ver"),
    )
