"""Errores de dominio del timeline (envelope {code, message})."""

from app.core.errors import DomainError


class EvidenceKindMismatchError(DomainError):
    # Al "editar" (versionar) no se puede cambiar el tipo del ítem (command/note).
    code = "evidence_kind_mismatch"
    status_code = 409
    default_message = "El tipo de evidencia no coincide con el del ítem"
