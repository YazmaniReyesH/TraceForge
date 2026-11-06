"""Sugerencia de IA sobre la evidencia de una sesión (F1-T4a).

Primera función de IA de producto: a partir de la evidencia real de una sesión, la IA **propone**
(ADR-0004) una descripción o un siguiente paso. Toda sugerencia nace con **procedencia completa**
(ADR-0003) y en estado ``pending`` hasta que un humano la **acepta** o la **edita**. El contenido
sugerido original NUNCA se sobrescribe: la edición humana vive en ``edited_content`` y se conserva
el rastro de origen IA (proveedor, modelo, versión de prompt, la llamada que la originó y las
entradas usadas, ya redactadas).

Qué NO se expone ni se guarda aquí: valores crudos de secretos. La evidencia enviada al proveedor va
**ya redactada**; el mapeo marcador→valor se guarda **cifrado** en ``ai_redaction_maps`` (ADR-0016),
nunca en esta tabla. ``suggested_payload`` es la salida estructurada **validada** del modelo
(ADR-0004); como se generó sobre evidencia redactada, puede contener marcadores pero nunca secretos.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import AISuggestionKind, AISuggestionStatus, sql_in_clause
from app.models.mixins import TimestampMixin
from app.models.types import StrEnumType


class AISuggestion(TimestampMixin, Base):
    """Una sugerencia de IA (pending → accepted/edited) con su procedencia."""

    __tablename__ = "ai_suggestions"

    ai_suggestion_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Aislamiento (ADR-0002): toda sugerencia pertenece a un workspace y a un project.
    # ON DELETE CASCADE: coherente con el borrado del contenido del project (ADR-0006).
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False, index=True
    )
    # La sesión cuya evidencia originó la sugerencia.
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[AISuggestionKind] = mapped_column(
        StrEnumType(AISuggestionKind, length=20), nullable=False
    )
    status: Mapped[AISuggestionStatus] = mapped_column(
        StrEnumType(AISuggestionStatus, length=20), nullable=False
    )

    # Contenido SUGERIDO por la IA (texto canónico). Inmutable: nunca se sobrescribe.
    suggested_content: Mapped[str] = mapped_column(Text, nullable=False)
    # Salida estructurada VALIDADA del modelo (ADR-0004), para procedencia y campos futuros
    # (p. ej. el ``rationale`` de next_step). Segura: se generó sobre evidencia redactada.
    suggested_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Contenido EDITADO por un humano (solo cuando status=edited). El original se conserva arriba.
    edited_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Procedencia (ADR-0003) ──
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)  # el que resolvió la API
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)  # p. ej. description/v1
    # Llamada de la bitácora (F1-T3) que originó la sugerencia. SET NULL: purgar la bitácora no
    # debe borrar la sugerencia (conserva la procedencia aunque se pierda el detalle de la llamada).
    ai_call_log_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_call_log.ai_call_log_id", ondelete="SET NULL"), nullable=True
    )
    # Referencia a las entradas usadas (evidencia ya redactada): {session_id, evidence:[{id,ver}]}.
    input_refs: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Cuántos secretos se enmascararon al redactar la evidencia (métrica; sin valores).
    redaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # True si se persistió el mapeo de redacción cifrado para esta sugerencia (ADR-0016). False si
    # no había secretos o si no había clave de cifrado (degradación segura: no se guardó en claro).
    redaction_map_stored: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ── Auditoría de la transición (ADR-0003) ──
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            f"kind IN ({sql_in_clause(AISuggestionKind)})", name="ck_ai_suggestions_kind"
        ),
        CheckConstraint(
            f"status IN ({sql_in_clause(AISuggestionStatus)})", name="ck_ai_suggestions_status"
        ),
    )
