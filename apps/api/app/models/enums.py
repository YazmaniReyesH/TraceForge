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


def sql_in_clause(enum: type[StrEnum]) -> str:
    """Devuelve ``'a', 'b', ...`` con los valores del enum, para un CHECK ``IN``."""
    return ", ".join(repr(member.value) for member in enum)
