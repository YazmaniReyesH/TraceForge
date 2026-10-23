"""Errores de dominio de projects y membresías de proyecto (envelope {code, message})."""

from app.core.errors import DomainError


class ProjectError(DomainError):
    """Base de los errores de projects."""


class UserNotFoundError(ProjectError):
    code = "user_not_found"
    status_code = 404
    default_message = "Usuario no encontrado"


class NotWorkspaceMemberError(ProjectError):
    code = "not_workspace_member"
    status_code = 409
    default_message = "El usuario no es miembro del workspace"


class GuestMustBeViewerError(ProjectError):
    # Regla dura (ADR-0002); reclasificada de 422 a 409 en F0-T5a (conflicto de negocio).
    code = "guest_must_be_viewer"
    status_code = 409
    default_message = "Un invitado (guest) solo puede ser viewer del proyecto"


class ProjectMemberExistsError(ProjectError):
    code = "member_exists"
    status_code = 409
    default_message = "El usuario ya es miembro del proyecto"
