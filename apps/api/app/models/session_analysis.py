"""Caché del análisis de contexto de una sesión (F1-T4c, ADR-0017).

El análisis de contexto es **efímero y desechable** (guía viva, NO contenido aprobable como las
sugerencias de F1-T4a): cada análisis refleja el estado de la evidencia en ese instante. Esta tabla
es **caché/optimización**, no una sugerencia con máquina de estados.

Una fila **por sesión** (la última): se sobrescribe en cada re-análisis. Guarda el ``state_hash``
del estado analizable (para el *hash-guard*: si el hash coincide y no hay ``force``, se devuelve sin
llamar a la API), el **resultado estructurado** de 4 bloques (JSONB, ya validado, ADR-0004), la
**procedencia** (ADR-0003: proveedor, modelo, versión de prompt, la llamada que lo originó) y, si
hubo secretos y clave, el **mapeo de redacción cifrado** (Fernet, ADR-0016) para rehidratación
futura. Nunca se guardan valores crudos ni la clave. Aislamiento por workspace/project.
"""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin


class SessionAnalysis(TimestampMixin, Base):
    """Último análisis de contexto de una sesión (caché; una fila por sesión)."""

    __tablename__ = "ai_session_analyses"

    ai_session_analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    # Aislamiento (ADR-0002). CASCADE coherente con el borrado del contenido del project (ADR-0006).
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Una fila por sesión: UNIQUE. Al re-analizar, se sobrescribe esta misma fila.
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Hash del estado analizable (ítems activos: id + versión actual + posición, EN ORDEN) + versión
    # de prompt. Es la clave del hash-guard: mismo hash y sin force => se devuelve este resultado.
    state_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Resultado estructurado VALIDADO de 4 bloques (ADR-0004). Seguro: se generó sobre evidencia
    # redactada (puede contener marcadores, nunca secretos).
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    analyzed_item_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # ── Procedencia (ADR-0003) ──
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    # SET NULL: purgar la bitácora no borra el análisis (conserva la procedencia resumida).
    ai_call_log_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_call_log.ai_call_log_id", ondelete="SET NULL"), nullable=True
    )

    # ── Redacción (ADR-0005/0016) ──
    redaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Mapeo marcador→valor CIFRADO (Fernet). NULL si no hubo secretos o si faltaba la clave
    # (degradación segura: jamás en claro). Reusa el mecanismo de ADR-0016 sin tocar la tabla parada
    # ``ai_redaction_maps`` (ligada a sugerencias); aquí el mapeo es 1:1 con el análisis efímero.
    redaction_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    redaction_scheme: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False
    )
