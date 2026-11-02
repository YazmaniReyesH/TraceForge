"""Servicio del timeline: reglas de negocio (append-only, hash, versión, soft-delete)."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import EvidenceItem, EvidenceItemVersion, Session
from app.timeline.errors import EvidenceKindMismatchError
from app.timeline.hashing import compute_content_hash
from app.timeline.repository import TimelineRepository
from app.timeline.schemas import (
    EvidenceItemCreate,
    EvidenceItemDetailRead,
    EvidenceItemRead,
    EvidenceItemVersionRead,
    SessionRead,
)


def _version_read(version: EvidenceItemVersion) -> EvidenceItemVersionRead:
    return EvidenceItemVersionRead.model_validate(version)


def _item_read(item: EvidenceItem, current: EvidenceItemVersion) -> EvidenceItemRead:
    return EvidenceItemRead(
        evidence_item_id=item.evidence_item_id,
        session_id=item.session_id,
        kind=item.kind,
        position=item.position,
        current_version=item.current_version,
        created_by=item.created_by,
        created_at=item.created_at,
        current=_version_read(current),
    )


class TimelineService:
    """Sesiones e ítems de evidencia de un project (acceso ya gate'd por el router)."""

    def __init__(
        self, repository: TimelineRepository, session: AsyncSession, user_id: UUID
    ) -> None:
        self._repo = repository
        self._db = session
        self._user_id = user_id

    # ── Sesiones ──
    async def create_session(self, *, name: str) -> SessionRead:
        obj = self._repo.add_session(name=name)
        await self._db.commit()
        return SessionRead.model_validate(obj)

    async def list_sessions(self) -> list[SessionRead]:
        rows = await self._repo.list_sessions()
        return [SessionRead.model_validate(s) for s in rows]

    async def rename_session(self, *, session_id: UUID, name: str) -> SessionRead:
        obj = await self._require_session(session_id)
        obj.name = name
        await self._db.commit()
        return SessionRead.model_validate(obj)

    async def delete_session(self, *, session_id: UUID) -> None:
        obj = await self._require_session(session_id)
        obj.deleted_at = datetime.now(UTC)  # soft-delete (cadena de custodia)
        await self._db.commit()

    # ── Ítems de evidencia ──
    async def add_item(self, *, session_id: UUID, data: EvidenceItemCreate) -> EvidenceItemRead:
        await self._require_session(session_id)
        position = await self._repo.next_position(session_id)
        item = self._repo.add_item(
            session_id=session_id, kind=data.kind, position=position, created_by=self._user_id
        )
        await self._repo.flush()  # asegura evidence_item_id antes de la versión (FK)
        version = self._repo.add_version(
            evidence_item_id=item.evidence_item_id,
            version=1,
            content_hash=self._hash(data),
            captured_at=data.captured_at or datetime.now(UTC),
            created_by=self._user_id,
            command_text=data.command_text,
            command_output=data.command_output,
            tool=data.tool,
            language=data.language,
            note_text=data.note_text,
        )
        await self._db.commit()
        return _item_read(item, version)

    async def list_items(self, *, session_id: UUID) -> list[EvidenceItemRead]:
        await self._require_session(session_id)
        rows = await self._repo.list_items_with_current(session_id)
        return [_item_read(item, current) for item, current in rows]

    async def get_item(
        self, *, session_id: UUID, item_id: UUID, include_history: bool
    ) -> EvidenceItemRead:
        await self._require_session(session_id)
        item = await self._require_item(session_id, item_id)
        current = await self._require_version(item.evidence_item_id, item.current_version)
        if not include_history:
            return _item_read(item, current)
        versions = await self._repo.list_versions(item.evidence_item_id)
        base = _item_read(item, current)
        return EvidenceItemDetailRead(
            **base.model_dump(), history=[_version_read(v) for v in versions]
        )

    async def edit_item(
        self, *, session_id: UUID, item_id: UUID, data: EvidenceItemCreate
    ) -> EvidenceItemRead:
        """Edición = versión NUEVA (append-only). No cambia el tipo del ítem."""
        await self._require_session(session_id)
        item = await self._require_item(session_id, item_id)
        if data.kind != item.kind:
            raise EvidenceKindMismatchError
        new_version = item.current_version + 1
        version = self._repo.add_version(
            evidence_item_id=item.evidence_item_id,
            version=new_version,
            content_hash=self._hash(data),
            captured_at=data.captured_at or datetime.now(UTC),
            created_by=self._user_id,
            command_text=data.command_text,
            command_output=data.command_output,
            tool=data.tool,
            language=data.language,
            note_text=data.note_text,
        )
        item.current_version = new_version  # puntero (bookkeeping); el contenido no se mutó
        await self._db.commit()
        return _item_read(item, version)

    async def delete_item(self, *, session_id: UUID, item_id: UUID) -> None:
        await self._require_session(session_id)
        item = await self._require_item(session_id, item_id)
        item.deleted_at = datetime.now(UTC)  # soft-delete
        await self._db.commit()

    # ── Helpers ──
    @staticmethod
    def _hash(data: EvidenceItemCreate) -> str:
        return compute_content_hash(
            data.kind,
            command_text=data.command_text,
            command_output=data.command_output,
            note_text=data.note_text,
        )

    async def _require_session(self, session_id: UUID) -> Session:
        obj = await self._repo.get_session(session_id)
        if obj is None:
            raise NotFoundError("Sesión no encontrada")
        return obj

    async def _require_item(self, session_id: UUID, item_id: UUID) -> EvidenceItem:
        obj = await self._repo.get_item(session_id, item_id)
        if obj is None:
            raise NotFoundError("Ítem de evidencia no encontrado")
        return obj

    async def _require_version(self, item_id: UUID, version: int) -> EvidenceItemVersion:
        obj = await self._repo.get_version(item_id, version)
        if obj is None:  # defensivo: un ítem vivo siempre tiene su versión vigente
            raise NotFoundError("Versión de evidencia no encontrada")
        return obj
