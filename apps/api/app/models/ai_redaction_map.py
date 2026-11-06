"""Almacén CIFRADO del mapeo de redacción marcador→valor (F1-T4a, ADR-0016).

Cuando fluye evidencia real hacia el proveedor, la redacción (ADR-0005) reemplaza cada secreto por
un marcador estable y produce un mapa ``marcador→valor real``. Para poder **rehidratar** esos
valores a un usuario autorizado más adelante (función futura), el mapa se guarda **cifrado**
(Fernet), asociado a la sugerencia y a la sesión/evidencia de la que salió. **Nunca** se guarda en
claro: la columna ``ciphertext`` es el token cifrado; la clave vive solo en el entorno
(``TF_ENCRYPTION_KEY``), jamás en la base ni en el repo.

Una fila por sugerencia que tuvo secretos (append-only en la práctica). Si no hay clave configurada,
NO se crea la fila (el valor crudo nunca se persiste): la generación degrada avisando (ADR-0016).
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import CreatedAtMixin


class AIRedactionMap(CreatedAtMixin, Base):
    """Mapeo marcador→valor **cifrado** de una generación de IA (para rehidratación futura)."""

    __tablename__ = "ai_redaction_maps"

    ai_redaction_map_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    # Aislamiento (ADR-0002) + CASCADE coherente con el borrado del project (ADR-0006).
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True
    )
    # La sugerencia cuya evidencia produjo este mapeo (1:1 en la práctica).
    ai_suggestion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_suggestions.ai_suggestion_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Token CIFRADO del JSON ``{marcador: valor}``. NUNCA en claro.
    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    # Esquema de cifrado (para rotación futura): hoy ``fernet``.
    scheme: Mapped[str] = mapped_column(String(20), nullable=False)
    # Cuántos marcadores contiene el mapa (métrica; sin valores).
    marker_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False
    )
