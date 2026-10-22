"""Errores de dominio de autenticación. El router los traduce a HTTP."""


class AuthError(Exception):
    """Base de los errores de autenticación."""


class EmailAlreadyRegisteredError(AuthError):
    """Ya existe un usuario con ese email (normalizado)."""


class InvalidCredentialsError(AuthError):
    """Email o contraseña inválidos. Mensaje genérico: no revela cuál falló."""
