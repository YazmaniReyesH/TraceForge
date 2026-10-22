"""Puerto de dominio ``AuthProvider`` (ADR-0007).

Interfaz que abstrae *cómo* se verifica una identidad. Hoy solo existe la
implementación local (email + contraseña, ver ``local_provider.py``). Un proveedor
**SSO** futuro (OIDC/SAML) sería otra implementación de esta misma interfaz —el
servicio y los endpoints no cambian— resolviendo/creando la identidad a partir de los
claims del proveedor en lugar de una contraseña.

El email que recibe el puerto ya viene **normalizado** por el servicio.
"""

from abc import ABC, abstractmethod

from app.models import User


class AuthProvider(ABC):
    """Puerto de autenticación: registrar y autenticar una identidad."""

    @abstractmethod
    async def register(self, *, email: str, password: str, display_name: str) -> User:
        """Crea la identidad y su credencial. Lanza ``EmailAlreadyRegistered`` si ya existe."""
        ...

    @abstractmethod
    async def authenticate(self, *, email: str, password: str) -> User | None:
        """Devuelve el ``User`` si las credenciales son válidas; ``None`` si no."""
        ...
