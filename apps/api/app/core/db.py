"""Capa de acceso a la base de datos: engine async, sesiones y Base declarativa.

TraceForge usa **SQLAlchemy 2 en modo async** sobre PostgreSQL con el driver
**asyncpg** (ver ADR-0001). Todo el backend es async y consistente: nada de
sesiones sync mezcladas.

En F0-T2 aún no hay modelos ni tablas; aquí solo queda la infraestructura de
conexión y la verificación de readiness. Los modelos de los módulos heredarán de
``Base`` a partir de F0-T3.
"""

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

_settings = get_settings()

# Engine async único de la aplicación. `pool_pre_ping` evita usar conexiones
# muertas (p. ej. tras reiniciar el contenedor de la base).
engine: AsyncEngine = create_async_engine(
    _settings.database_url,
    pool_pre_ping=True,
    future=True,
)

# Fábrica de sesiones async. `expire_on_commit=False` para poder seguir usando
# los objetos tras el commit sin recargarlos.
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base declarativa de la que heredan todos los modelos de TraceForge."""


def get_engine() -> AsyncEngine:
    """Devuelve el engine async de la app.

    Expuesto como dependencia para poder sustituirlo en pruebas
    (``app.dependency_overrides``).
    """
    return engine


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dependencia FastAPI: entrega una sesión async por request y la cierra."""
    async with AsyncSessionLocal() as session:
        yield session


async def database_ready(engine: AsyncEngine) -> bool:
    """Comprueba la conexión a la base con un ``SELECT 1``.

    Devuelve ``True`` si la base responde; ``False`` ante cualquier fallo de
    conexión/ejecución. No propaga la excepción: readiness decide el HTTP.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        return False
    return True
