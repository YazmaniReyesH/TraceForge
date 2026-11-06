"""Enums de dominio del modelo base.

Un ``StrEnum`` por conjunto de roles (ADR-0002). Los valores son EXACTAMENTE los
que aparecen en los CHECK constraints de las tablas de membresía; los CHECK se
generan a partir de estos enums para que no haya desincronización.
"""

from enum import StrEnum


class WorkspaceRole(StrEnum):
    """Roles a nivel de workspace (ADR-0002)."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"


class ProjectRole(StrEnum):
    """Roles a nivel de proyecto (ADR-0002)."""

    LEAD = "lead"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"


class EvidenceKind(StrEnum):
    """Tipos de ítem de evidencia del timeline (F1). Solo texto en F1."""

    COMMAND = "command"  # comando + output
    NOTE = "note"  # texto libre


class AICallStatus(StrEnum):
    """Estado de una llamada registrada en la bitácora de IA (F1-T3)."""

    OK = "ok"  # el proveedor completó la solicitud
    ERROR = "error"  # error de red/API del proveedor (traducido, sin secretos)
    NOT_CONFIGURED = "not_configured"  # no hay API key: se degradó sin llamar al proveedor


class AISuggestionKind(StrEnum):
    """Tipo de sugerencia de IA generada sobre la evidencia de una sesión (F1-T4a)."""

    DESCRIPTION = "description"  # descripción de la evidencia de la sesión (la principal)
    NEXT_STEP = "next_step"  # sugerencia de siguiente paso


class AISuggestionStatus(StrEnum):
    """Estado de una sugerencia de IA (ADR-0003: nace pendiente de revisión humana).

    Máquina de estados (F1-T4a): ``pending`` → ``accepted`` o ``edited``; ``edited`` admite
    re-edición (``edited`` → ``edited``) conservando siempre el contenido sugerido original;
    ``accepted`` es terminal. Cualquier otra transición es un error de dominio (409).
    """

    PENDING = "pending"  # recién generada; aún no revisada por un humano
    ACCEPTED = "accepted"  # un humano la aceptó tal cual
    EDITED = "edited"  # un humano la editó (se conserva el original + el rastro de origen IA)


class SessionPhase(StrEnum):
    """Fase del pentest inferida por la IA a partir de la evidencia de la sesión (F1-T4c).

    Valor **sugerido** por el modelo y **validado** por el código (ADR-0004): la salida del análisis
    debe traer exactamente uno de estos valores o se rechaza como forma inválida.
    """

    RECON = "recon"
    ENUMERATION = "enumeración"
    FOOTHOLD = "foothold"
    PRIVESC = "privesc"
    OTHER = "otra"


def sql_in_clause(enum: type[StrEnum]) -> str:
    """Devuelve ``'a', 'b', ...`` con los valores del enum, para un CHECK ``IN``."""
    return ", ".join(repr(member.value) for member in enum)
