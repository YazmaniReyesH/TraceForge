"""Mapeo de ``IntegrityError`` de la base → errores de dominio, **por nombre de constraint**.

Reemplaza el ``except IntegrityError`` catch-all (deuda de F0-T4a): cada servicio declara
qué constraint se traduce a qué error de dominio; una violación desconocida se **re-lanza**
tal cual (no se enmascara). Reutilizable por los módulos de F0-T4b-2 (único de membresía,
índice parcial de owner, CHECK de roles).
"""

from collections.abc import Callable, Mapping

from sqlalchemy.exc import IntegrityError


def constraint_name(exc: IntegrityError) -> str | None:
    """Extrae el nombre de la constraint violada del error de asyncpg, si está disponible.

    El nombre vive en la excepción original de asyncpg (``exc.orig.__cause__``), no siempre
    en el wrapper de SQLAlchemy; por eso se revisan ambos.
    """
    candidates = (exc.orig, getattr(exc.orig, "__cause__", None))
    for candidate in candidates:
        name = getattr(candidate, "constraint_name", None)
        if name:
            return str(name)
    return None


def translate_integrity_error(
    exc: IntegrityError,
    mapping: Mapping[str, Callable[[], Exception]],
) -> Exception:
    """Devuelve el error de dominio para la constraint violada, o el mismo ``exc`` si no mapea.

    Uso típico en un servicio::

        try:
            await session.commit()
        except IntegrityError as exc:
            raise translate_integrity_error(exc, {"users_email_key": EmailAlreadyRegisteredError})

    Si la constraint no está en el mapa, se devuelve ``exc`` para re-lanzarla sin enmascararla.
    """
    name = constraint_name(exc)
    if name is not None and name in mapping:
        return mapping[name]()
    return exc
