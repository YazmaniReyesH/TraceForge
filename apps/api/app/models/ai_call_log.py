"""Bitácora de llamadas de IA (F1-T3): auditoría de cada invocación al proveedor (ADR-0005).

Registra, por llamada, **qué se envió YA REDACTADO** y metadatos (proveedor, modelo, estado,
tokens, usuario, workspace/project para aislamiento y auditoría). **Nunca** guarda el contenido sin
redactar, el mapeo marcador→valor real ni la API key. En la práctica es *append-only*: se inserta
una fila por llamada y no se vuelve a tocar.

Qué se guarda y por qué (ADR-0015): además del prompt **ya redactado** (lo mismo que cruzó el
perímetro; nunca más que eso), su ``content_hash`` SHA-256 (integridad/deduplicación) y el número de
secretos enmascarados (métrica de la redacción, sin revelar valores). Guardar el texto redactado da
valor de auditoría real ("¿qué enviamos?") sin exposición nueva: ya salió al proveedor y vive en el
mismo perímetro que la evidencia. Lo que jamás entra es el valor crudo ni el mapeo.
"""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import AICallStatus, sql_in_clause
from app.models.mixins import CreatedAtMixin
from app.models.types import StrEnumType


class AICallLog(CreatedAtMixin, Base):
    """Una fila por llamada de IA (auditoría; append-only en la práctica)."""

    __tablename__ = "ai_call_log"

    ai_call_log_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Aislamiento: toda llamada pertenece a un workspace y a un project (ADR-0002).
    # ON DELETE CASCADE: coherente con el borrado del contenido del project (ver ADR-0006).
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[AICallStatus] = mapped_column(
        StrEnumType(AICallStatus, length=20), nullable=False
    )
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Lo que se envió, YA REDACTADO (nunca el crudo). None si no se llegó a enviar (not_configured).
    redacted_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    # SHA-256 (hex) del prompt redactado: integridad/deduplicación de lo enviado.
    redacted_prompt_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Cuántos secretos se enmascararon (métrica; sin revelar valores).
    redaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Código de error de dominio (estable); NUNCA un mensaje con secretos. None si status=ok.
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            f"status IN ({sql_in_clause(AICallStatus)})",
            name="ck_ai_call_log_status",
        ),
    )
