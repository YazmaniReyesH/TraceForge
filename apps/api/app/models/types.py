"""Tipos SQLAlchemy reutilizables.

``StrEnumType`` almacena un ``StrEnum`` como ``VARCHAR`` (impl = String) pero
devuelve el miembro del enum al leer. Así cerramos la nota de F0-T3b (que ``role``
se leyera como ``str`` plano) SIN cambiar el tipo de columna (sigue siendo
``VARCHAR(n)``), por lo que no requiere migración. El CHECK de valores sigue
viviendo como constraint nombrado en cada tabla.
"""

import enum
from typing import Any

from sqlalchemy import String
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class StrEnumType(TypeDecorator[enum.StrEnum]):
    """Mapea un ``StrEnum`` <-> ``VARCHAR`` conservando el tipo de columna."""

    impl = String
    cache_ok = True

    def __init__(self, enum_class: type[enum.StrEnum], *, length: int = 20) -> None:
        self._enum_class = enum_class
        super().__init__(length=length)

    def process_bind_param(self, value: Any, dialect: Dialect) -> str | None:
        """Python -> BD: guarda el valor del enum (valida que sea un miembro)."""
        if value is None:
            return None
        return self._enum_class(value).value

    def process_result_value(self, value: Any, dialect: Dialect) -> enum.StrEnum | None:
        """BD -> Python: reconstruye el miembro del enum."""
        if value is None:
            return None
        return self._enum_class(value)
