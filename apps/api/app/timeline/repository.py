"""Repositorio del timeline (única capa que toca la BD). Acotado al ``project_id`` del contexto.

Aislamiento: las sesiones se filtran por ``project_id`` (el acceso al project ya lo validó el gate
de proyecto); los ítems/versiones se acotan a su sesión. Nunca se hace UPDATE del contenido de una
versión (append-only): "editar" inserta una versión nueva; "borrar" marca ``deleted_at``.
"""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Row, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EvidenceItem, EvidenceItemVersion, Session
from app.models.enums import EvidenceKind

# Escala de orden con huecos (ADR-0013). El append normal salta de STEP en STEP; insertar "entre
# dos" toma el punto medio; la base 0 es el borde izquierdo virtual (antes del primer ítem).
POSITION_STEP = 1000
POSITION_BASE = 0

# Orden determinista del timeline: por posición y, ante empate, por antigüedad e id (estable).
_ITEM_ORDER = (EvidenceItem.position, EvidenceItem.created_at, EvidenceItem.evidence_item_id)


class TimelineRepository:
    """Acceso a datos de sesiones e ítems de evidencia de un project."""

    def __init__(self, session: AsyncSession, project_id: UUID) -> None:
        self._db = session
        self._project_id = project_id

    async def flush(self) -> None:
        await self._db.flush()

    # ── Sesiones ──
    def add_session(self, *, name: str) -> Session:
        obj = Session(session_id=uuid4(), project_id=self._project_id, name=name)
        self._db.add(obj)
        return obj

    async def get_session(self, session_id: UUID) -> Session | None:
        """Sesión viva del project del contexto (aislamiento)."""
        stmt = select(Session).where(
            Session.session_id == session_id,
            Session.project_id == self._project_id,
            Session.deleted_at.is_(None),
        )
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def list_sessions(self) -> Sequence[Session]:
        stmt = (
            select(Session)
            .where(Session.project_id == self._project_id, Session.deleted_at.is_(None))
            .order_by(Session.created_at)
        )
        return (await self._db.execute(stmt)).scalars().all()

    # ── Ítems: orden/posición (escala con huecos, ADR-0013) ──
    async def max_position(self, session_id: UUID) -> int | None:
        """Mayor posición entre los ítems vivos de la sesión (None si no hay)."""
        stmt = select(func.max(EvidenceItem.position)).where(
            EvidenceItem.session_id == session_id, EvidenceItem.deleted_at.is_(None)
        )
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def next_position(self, session_id: UUID) -> int:
        """Posición para **añadir al final** (append): último hueco + STEP, o STEP si está vacía."""
        current_max = await self.max_position(session_id)
        return POSITION_BASE + POSITION_STEP if current_max is None else current_max + POSITION_STEP

    async def min_position(
        self, session_id: UUID, *, exclude_item_id: UUID | None = None
    ) -> int | None:
        """Menor posición entre los ítems vivos (excluyendo opcionalmente uno que se mueve)."""
        stmt = select(func.min(EvidenceItem.position)).where(
            EvidenceItem.session_id == session_id, EvidenceItem.deleted_at.is_(None)
        )
        if exclude_item_id is not None:
            stmt = stmt.where(EvidenceItem.evidence_item_id != exclude_item_id)
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def next_higher_position(
        self, session_id: UUID, position: int, *, exclude_item_id: UUID | None = None
    ) -> int | None:
        """Menor posición estrictamente mayor que ``position`` (vecino derecho); None si no hay."""
        stmt = select(func.min(EvidenceItem.position)).where(
            EvidenceItem.session_id == session_id,
            EvidenceItem.deleted_at.is_(None),
            EvidenceItem.position > position,
        )
        if exclude_item_id is not None:
            stmt = stmt.where(EvidenceItem.evidence_item_id != exclude_item_id)
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def items_for_renumber(self, session_id: UUID) -> Sequence[EvidenceItem]:
        """Ítems vivos de la sesión en orden determinista, para reasignar sus posiciones."""
        stmt = (
            select(EvidenceItem)
            .where(EvidenceItem.session_id == session_id, EvidenceItem.deleted_at.is_(None))
            .order_by(*_ITEM_ORDER)
        )
        return (await self._db.execute(stmt)).scalars().all()

    def add_item(
        self, *, session_id: UUID, kind: EvidenceKind, position: int, created_by: UUID
    ) -> EvidenceItem:
        obj = EvidenceItem(
            evidence_item_id=uuid4(),
            session_id=session_id,
            kind=kind,
            position=position,
            current_version=1,
            created_by=created_by,
        )
        self._db.add(obj)
        return obj

    def add_version(
        self,
        *,
        evidence_item_id: UUID,
        version: int,
        content_hash: str,
        captured_at: datetime,
        created_by: UUID,
        command_text: str | None,
        command_output: str | None,
        tool: str | None,
        language: str | None,
        note_text: str | None,
    ) -> EvidenceItemVersion:
        obj = EvidenceItemVersion(
            evidence_item_version_id=uuid4(),
            evidence_item_id=evidence_item_id,
            version=version,
            content_hash=content_hash,
            captured_at=captured_at,
            created_by=created_by,
            command_text=command_text,
            command_output=command_output,
            tool=tool,
            language=language,
            note_text=note_text,
        )
        self._db.add(obj)
        return obj

    async def get_item(self, session_id: UUID, item_id: UUID) -> EvidenceItem | None:
        stmt = select(EvidenceItem).where(
            EvidenceItem.evidence_item_id == item_id,
            EvidenceItem.session_id == session_id,
            EvidenceItem.deleted_at.is_(None),
        )
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def list_items_with_current(
        self, session_id: UUID
    ) -> Sequence[Row[tuple[EvidenceItem, EvidenceItemVersion]]]:
        """Ítems vivos en orden, con su versión vigente (join; sin N+1)."""
        stmt = (
            select(EvidenceItem, EvidenceItemVersion)
            .join(
                EvidenceItemVersion,
                (EvidenceItemVersion.evidence_item_id == EvidenceItem.evidence_item_id)
                & (EvidenceItemVersion.version == EvidenceItem.current_version),
            )
            .where(EvidenceItem.session_id == session_id, EvidenceItem.deleted_at.is_(None))
            .order_by(*_ITEM_ORDER)
        )
        return (await self._db.execute(stmt)).all()

    async def get_version(self, item_id: UUID, version: int) -> EvidenceItemVersion | None:
        stmt = select(EvidenceItemVersion).where(
            EvidenceItemVersion.evidence_item_id == item_id,
            EvidenceItemVersion.version == version,
        )
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def list_versions(self, item_id: UUID) -> Sequence[EvidenceItemVersion]:
        stmt = (
            select(EvidenceItemVersion)
            .where(EvidenceItemVersion.evidence_item_id == item_id)
            .order_by(EvidenceItemVersion.version)
        )
        return (await self._db.execute(stmt)).scalars().all()
