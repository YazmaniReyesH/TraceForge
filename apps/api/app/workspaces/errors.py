"""Errores de dominio de workspaces y membresías. El router los traduce a HTTP."""


class WorkspaceError(Exception):
    """Base de los errores de workspaces."""


class UserNotFoundError(WorkspaceError):
    """No existe un usuario con ese email (alta de miembro)."""


class MemberExistsError(WorkspaceError):
    """El usuario ya es miembro del workspace."""


class NotWorkspaceMemberError(WorkspaceError):
    """El usuario objetivo no es miembro del workspace."""


class CannotAssignOwnerRoleError(WorkspaceError):
    """No se asigna ``owner`` directamente: la propiedad se mueve por transferencia."""


class CannotModifySoleOwnerError(WorkspaceError):
    """No se puede degradar ni quitar al único owner (invariante "al menos un owner")."""


class AlreadyOwnerError(WorkspaceError):
    """El destinatario de la transferencia ya es el owner."""
