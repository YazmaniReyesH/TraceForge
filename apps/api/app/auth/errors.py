"""Errores de dominio de autenticación (envelope {code, message} vía DomainError)."""

from app.core.errors import DomainError


class AuthError(DomainError):
    """Base de los errores de autenticación."""


class EmailAlreadyRegisteredError(AuthError):
    code = "email_already_registered"
    status_code = 409
    default_message = "Ese correo ya está registrado"


class InvalidCredentialsError(AuthError):
    code = "invalid_credentials"
    status_code = 401
    default_message = "Credenciales inválidas"
