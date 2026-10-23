"""Errores de dominio de usuarios (envelope {code, message})."""

from app.core.errors import DomainError


class UserError(DomainError):
    """Base de los errores de usuarios."""


class UserNotFoundError(UserError):
    code = "user_not_found"
    status_code = 404
    default_message = "Usuario no encontrado"


class UserHasMembershipsError(UserError):
    code = "user_has_memberships"
    status_code = 409
    default_message = "El usuario tiene membresías: no puede borrarse"
