"""Errores de dominio de usuarios."""


class UserError(Exception):
    """Base de los errores de usuarios."""


class UserNotFoundError(UserError):
    """No existe el usuario."""


class UserHasMembershipsError(UserError):
    """El usuario tiene membresías (workspace o proyecto): no puede borrarse (RESTRICT).

    El flujo seguro de baja (revocar membresías / transferir titularidades) es de otra fase.
    """
