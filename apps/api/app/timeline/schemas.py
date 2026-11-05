"""Schemas Pydantic del timeline (sesiones e ítems de evidencia)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import EvidenceKind

# Tope de tamaño de los campos de texto (~1 MB en UTF-8 de 1 byte). Generoso para outputs de
# escaneos grandes, pero acotado para limitar el tamaño de request/fila y evitar abuso; evidencia
# mayor pertenece a almacenamiento de objetos (diferido en F1).
TEXT_MAX = 1_000_000


# ── Sesiones ──


class SessionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class SessionUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: UUID
    project_id: UUID
    name: str
    created_at: datetime
    updated_at: datetime


# ── Ítems de evidencia ──


class EvidenceItemCreate(BaseModel):
    """Alta/edición de un ítem (en edición, el ``kind`` debe coincidir con el del ítem)."""

    kind: EvidenceKind
    command_text: str | None = Field(default=None, max_length=TEXT_MAX)
    command_output: str | None = Field(default=None, max_length=TEXT_MAX)
    tool: str | None = Field(default=None, max_length=100)
    language: str | None = Field(default=None, max_length=50)
    note_text: str | None = Field(default=None, max_length=TEXT_MAX)
    captured_at: datetime | None = None  # por defecto, ahora()
    # Inserción (solo en ALTA; se ignora al editar): None => añade al final; un id => inserta
    # justo después de ese ítem (escala con huecos, ADR-0013).
    after_item_id: UUID | None = None

    @model_validator(mode="after")
    def _require_content(self) -> "EvidenceItemCreate":
        if self.kind == EvidenceKind.COMMAND:
            if not self.command_text:
                raise ValueError("command_text es requerido para kind=command")
        elif not self.note_text:
            raise ValueError("note_text es requerido para kind=note")
        return self


class EvidenceItemMove(BaseModel):
    """Reordenamiento de un ítem: a dónde moverlo (solo cambia el orden, no el contenido)."""

    # None => al inicio (antes de todos); un id => justo después de ese ítem.
    # Para mover al final, el cliente pasa el id del último ítem.
    after_item_id: UUID | None


class EvidenceItemVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_item_version_id: UUID
    version: int
    content_hash: str
    captured_at: datetime
    command_text: str | None
    command_output: str | None
    tool: str | None
    language: str | None
    note_text: str | None
    created_by: UUID
    created_at: datetime


class EvidenceItemRead(BaseModel):
    """Ítem con su versión vigente (``current``)."""

    evidence_item_id: UUID
    session_id: UUID
    kind: EvidenceKind
    position: int
    current_version: int
    created_by: UUID
    created_at: datetime
    current: EvidenceItemVersionRead


class EvidenceItemDetailRead(EvidenceItemRead):
    """Detalle con el historial completo de versiones (si se solicita)."""

    history: list[EvidenceItemVersionRead]
