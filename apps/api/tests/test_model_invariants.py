"""Pruebas de los invariantes del modelo base a NIVEL DE BASE DE DATOS (ADR-0002).

Verifican que la base rechaza por sí misma (constraints/índices):

- email duplicado (UNIQUE en users.email),
- segundo ``owner`` en el mismo workspace (índice único parcial),
- membresía de workspace duplicada (UNIQUE user_id, workspace_id),
- membresía de proyecto duplicada (UNIQUE user_id, project_id).

Corren contra la base real: en local requieren `task up` **y** la migración aplicada
(`task db-upgrade`); en CI, el service container con la migración aplicada antes de las
pruebas. Si el esquema no está aplicado, cada prueba se **omite** (no falla), con un
mensaje que indica cómo habilitarlas.

Los invariantes de SERVICIO (guest = solo viewer, transferencia atómica de owner, "al
menos un owner") NO se prueban aquí: son de F0-T4.

Cada prueba corre en su propio event loop (``asyncio.run``) y dispone el engine dentro
del mismo loop (asyncpg liga conexiones al loop donde se crearon). No se hace commit:
todo ocurre en una transacción que se revierte, sin dejar residuo.
"""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.db import AsyncSessionLocal
from app.core.db import engine as app_engine
from app.models import (
    Project,
    ProjectMembership,
    ProjectRole,
    User,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
)


async def _schema_ready() -> bool:
    """True si la tabla ``users`` existe (proxy de 'migración aplicada')."""
    try:
        async with app_engine.connect() as conn:
            await conn.execute(text("SELECT 1 FROM users LIMIT 1"))
    except Exception:
        return False
    return True


def _skip_if_no_schema(ran: bool) -> None:
    if not ran:
        pytest.skip("Esquema no aplicado; corre `task up` y `task db-upgrade` para estas pruebas")


async def _duplicate_email() -> bool:
    try:
        if not await _schema_ready():
            return False
        async with AsyncSessionLocal() as session:
            email = f"dup-{uuid4()}@example.com"
            session.add(User(user_id=uuid4(), email=email, display_name="A"))
            await session.flush()
            session.add(User(user_id=uuid4(), email=email, display_name="B"))
            with pytest.raises(IntegrityError):
                await session.flush()
            await session.rollback()
        return True
    finally:
        await app_engine.dispose()


async def _second_owner() -> bool:
    try:
        if not await _schema_ready():
            return False
        async with AsyncSessionLocal() as session:
            ws_id = uuid4()
            u1, u2 = uuid4(), uuid4()
            session.add(Workspace(workspace_id=ws_id, name="WS"))
            session.add(User(user_id=u1, email=f"o1-{uuid4()}@example.com", display_name="O1"))
            session.add(User(user_id=u2, email=f"o2-{uuid4()}@example.com", display_name="O2"))
            await session.flush()
            session.add(
                WorkspaceMembership(user_id=u1, workspace_id=ws_id, role=WorkspaceRole.OWNER)
            )
            await session.flush()
            session.add(
                WorkspaceMembership(user_id=u2, workspace_id=ws_id, role=WorkspaceRole.OWNER)
            )
            with pytest.raises(IntegrityError):
                await session.flush()
            await session.rollback()
        return True
    finally:
        await app_engine.dispose()


async def _duplicate_workspace_membership() -> bool:
    try:
        if not await _schema_ready():
            return False
        async with AsyncSessionLocal() as session:
            ws_id, u_id = uuid4(), uuid4()
            session.add(Workspace(workspace_id=ws_id, name="WS"))
            session.add(User(user_id=u_id, email=f"m-{uuid4()}@example.com", display_name="M"))
            await session.flush()
            session.add(
                WorkspaceMembership(user_id=u_id, workspace_id=ws_id, role=WorkspaceRole.MEMBER)
            )
            await session.flush()
            # Mismo (user, workspace), aunque cambie el rol -> viola UNIQUE.
            session.add(
                WorkspaceMembership(user_id=u_id, workspace_id=ws_id, role=WorkspaceRole.ADMIN)
            )
            with pytest.raises(IntegrityError):
                await session.flush()
            await session.rollback()
        return True
    finally:
        await app_engine.dispose()


async def _duplicate_project_membership() -> bool:
    try:
        if not await _schema_ready():
            return False
        async with AsyncSessionLocal() as session:
            ws_id, pr_id, u_id = uuid4(), uuid4(), uuid4()
            session.add(Workspace(workspace_id=ws_id, name="WS"))
            session.add(User(user_id=u_id, email=f"p-{uuid4()}@example.com", display_name="P"))
            await session.flush()
            session.add(Project(project_id=pr_id, workspace_id=ws_id, name="PR"))
            await session.flush()
            session.add(ProjectMembership(user_id=u_id, project_id=pr_id, role=ProjectRole.VIEWER))
            await session.flush()
            session.add(
                ProjectMembership(user_id=u_id, project_id=pr_id, role=ProjectRole.CONTRIBUTOR)
            )
            with pytest.raises(IntegrityError):
                await session.flush()
            await session.rollback()
        return True
    finally:
        await app_engine.dispose()


def test_duplicate_email_rejected() -> None:
    """Un email repetido en toda la instancia es rechazado por la base."""
    _skip_if_no_schema(asyncio.run(_duplicate_email()))


def test_second_owner_in_workspace_rejected() -> None:
    """Un segundo ``owner`` en el mismo workspace es rechazado (índice parcial)."""
    _skip_if_no_schema(asyncio.run(_second_owner()))


def test_duplicate_workspace_membership_rejected() -> None:
    """Una membresía de workspace duplicada (user, workspace) es rechazada."""
    _skip_if_no_schema(asyncio.run(_duplicate_workspace_membership()))


def test_duplicate_project_membership_rejected() -> None:
    """Una membresía de proyecto duplicada (user, project) es rechazada."""
    _skip_if_no_schema(asyncio.run(_duplicate_project_membership()))
