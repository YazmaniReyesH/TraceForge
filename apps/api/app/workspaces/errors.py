"""Errores de dominio de workspaces y membresías (envelope {code, message})."""

from app.core.errors import DomainError


class WorkspaceError(DomainError):
    """Base de los errores de workspaces."""


class UserNotFoundError(WorkspaceError):
    code = "user_not_found"
    status_code = 404
    default_message = "Usuario no encontrado"


class MemberExistsError(WorkspaceError):
    code = "member_exists"
    status_code = 409
    default_message = "El usuario ya es miembro"


class NotWorkspaceMemberError(WorkspaceError):
    code = "not_a_member"
    status_code = 404
    default_message = "Miembro no encontrado"


class CannotAssignOwnerRoleError(WorkspaceError):
    code = "cannot_assign_owner"
    status_code = 409
    default_message = "El rol owner se asigna transfiriendo la propiedad"


class CannotModifySoleOwnerError(WorkspaceError):
    code = "sole_owner"
    status_code = 409
    default_message = "No puedes degradar ni quitar al único owner; transfiere la propiedad"


class AlreadyOwnerError(WorkspaceError):
    code = "already_owner"
    status_code = 409
    default_message = "Ese usuario ya es el owner"
