"""Errores de dominio de projects y de membresías de proyecto. El router los traduce a HTTP."""


class ProjectError(Exception):
    """Base de los errores de projects."""


class UserNotFoundError(ProjectError):
    """No existe un usuario con ese email (alta de miembro)."""


class NotWorkspaceMemberError(ProjectError):
    """El usuario no es miembro del workspace: no puede tener membresía de proyecto."""


class GuestMustBeViewerError(ProjectError):
    """Regla dura (ADR-0002): un guest de workspace solo puede ser ``viewer`` de proyecto."""


class ProjectMemberExistsError(ProjectError):
    """El usuario ya es miembro del proyecto."""
