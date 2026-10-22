"""Pruebas de los endpoints de workspaces y de la autorización, contra la base real.

Ejercitan: crear workspace ⇒ owner; aislamiento del listado entre dos usuarios; contexto de
autorización (404 a no-miembros / inexistente; 403 a miembro sin permiso) y 401 sin sesión.

Requieren el esquema aplicado (local `task up` + `task db-upgrade`; CI con migraciones). Si
falta, se omiten. Cada prueba limpia lo suyo en `finally` (borra workspaces -> cascada a
membresías- y luego usuarios) aunque falle, y no asume BD vacía.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, text

from app.core.db import AsyncSessionLocal
from app.core.db import engine as app_engine
from app.main import app
from app.models import User, Workspace, WorkspaceMembership
from app.models.enums import WorkspaceRole

_PW = "Sup3r-Secret-Pw!"


async def _schema_ready() -> bool:
    try:
        async with app_engine.connect() as conn:
            await conn.execute(text("SELECT 1 FROM user_credentials LIMIT 1"))
    except Exception:
        return False
    return True


@asynccontextmanager
async def _client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def _register(client: AsyncClient, email: str) -> dict[str, object]:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": _PW, "display_name": "U"},
    )
    assert resp.status_code == 201, resp.text
    body: dict[str, object] = resp.json()
    return body


async def _login(client: AsyncClient, email: str) -> None:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": _PW})
    assert resp.status_code == 200, resp.text


async def _cleanup(emails: list[str]) -> None:
    """Borra workspaces de esos usuarios (cascada a membresías) y luego los usuarios."""
    async with AsyncSessionLocal() as s:
        user_ids = (
            (await s.execute(select(User.user_id).where(User.email.in_(emails)))).scalars().all()
        )
        if user_ids:
            ws_ids = (
                (
                    await s.execute(
                        select(WorkspaceMembership.workspace_id).where(
                            WorkspaceMembership.user_id.in_(user_ids)
                        )
                    )
                )
                .scalars()
                .all()
            )
            if ws_ids:
                await s.execute(delete(Workspace).where(Workspace.workspace_id.in_(ws_ids)))
            await s.execute(delete(User).where(User.user_id.in_(user_ids)))
        await s.commit()


def test_create_workspace_makes_creator_owner() -> None:
    async def scenario() -> str:
        try:
            if not await _schema_ready():
                return "skip"
            email = f"ws-owner-{uuid4()}@example.com"
            try:
                async with _client() as client:
                    await _register(client, email)
                    await _login(client, email)
                    resp = await client.post("/api/v1/workspaces", json={"name": "Proyecto X"})
                    assert resp.status_code == 201, resp.text
                    body = resp.json()
                    assert body["name"] == "Proyecto X"
                    ws_id = body["workspace_id"]
                    # El creador puede leer el detalle (es owner).
                    detail = await client.get(f"/api/v1/workspaces/{ws_id}")
                    assert detail.status_code == 200
                # Verifica en BD que la membresía del creador es owner.
                async with AsyncSessionLocal() as s:
                    role = (
                        await s.execute(
                            select(WorkspaceMembership.role).where(
                                WorkspaceMembership.workspace_id == ws_id
                            )
                        )
                    ).scalar_one()
                    assert role == WorkspaceRole.OWNER
            finally:
                await _cleanup([email])
            return "ok"
        finally:
            await app_engine.dispose()

    if asyncio.run(scenario()) == "skip":
        pytest.skip("Falta el esquema; corre `task up` y `task db-upgrade`")


def test_list_is_isolated_between_users() -> None:
    async def scenario() -> str:
        try:
            if not await _schema_ready():
                return "skip"
            email_a = f"ws-a-{uuid4()}@example.com"
            email_b = f"ws-b-{uuid4()}@example.com"
            try:
                async with _client() as ca, _client() as cb:
                    await _register(ca, email_a)
                    await _login(ca, email_a)
                    await _register(cb, email_b)
                    await _login(cb, email_b)
                    a_ws = (await ca.post("/api/v1/workspaces", json={"name": "A"})).json()
                    await cb.post("/api/v1/workspaces", json={"name": "B"})
                    # A solo ve el suyo.
                    listing = await ca.get("/api/v1/workspaces")
                    assert listing.status_code == 200
                    names = [w["name"] for w in listing.json()]
                    ids = [w["workspace_id"] for w in listing.json()]
                    assert names == ["A"]
                    assert a_ws["workspace_id"] in ids
            finally:
                await _cleanup([email_a, email_b])
            return "ok"
        finally:
            await app_engine.dispose()

    if asyncio.run(scenario()) == "skip":
        pytest.skip("Falta el esquema; corre `task up` y `task db-upgrade`")


def test_detail_non_member_and_missing_return_404() -> None:
    async def scenario() -> str:
        try:
            if not await _schema_ready():
                return "skip"
            email_a = f"ws-na-{uuid4()}@example.com"
            email_b = f"ws-nb-{uuid4()}@example.com"
            try:
                async with _client() as ca, _client() as cb:
                    await _register(ca, email_a)
                    await _login(ca, email_a)
                    await _register(cb, email_b)
                    await _login(cb, email_b)
                    a_ws = (await ca.post("/api/v1/workspaces", json={"name": "A"})).json()
                    # B no es miembro del workspace de A -> 404 (no filtra existencia).
                    forbidden = await cb.get(f"/api/v1/workspaces/{a_ws['workspace_id']}")
                    assert forbidden.status_code == 404
                    # Workspace inexistente -> 404.
                    missing = await cb.get(f"/api/v1/workspaces/{uuid4()}")
                    assert missing.status_code == 404
            finally:
                await _cleanup([email_a, email_b])
            return "ok"
        finally:
            await app_engine.dispose()

    if asyncio.run(scenario()) == "skip":
        pytest.skip("Falta el esquema; corre `task up` y `task db-upgrade`")


def test_detail_member_without_permission_returns_403() -> None:
    async def scenario() -> str:
        try:
            if not await _schema_ready():
                return "skip"
            email_owner = f"ws-o-{uuid4()}@example.com"
            email_guest = f"ws-g-{uuid4()}@example.com"
            try:
                async with _client() as co, _client() as cg:
                    await _register(co, email_owner)
                    await _login(co, email_owner)
                    guest = await _register(cg, email_guest)
                    await _login(cg, email_guest)
                    a_ws = (await co.post("/api/v1/workspaces", json={"name": "A"})).json()
                    # Alta del guest como miembro directa (gestión de miembros: F0-T4b-2).
                    async with AsyncSessionLocal() as s:
                        s.add(
                            WorkspaceMembership(
                                workspace_membership_id=uuid4(),
                                user_id=guest["user_id"],
                                workspace_id=a_ws["workspace_id"],
                                role=WorkspaceRole.GUEST,
                            )
                        )
                        await s.commit()
                    # guest es miembro (contexto ok) pero su rol no puede leer -> 403.
                    resp = await cg.get(f"/api/v1/workspaces/{a_ws['workspace_id']}")
                    assert resp.status_code == 403, resp.text
            finally:
                await _cleanup([email_owner, email_guest])
            return "ok"
        finally:
            await app_engine.dispose()

    if asyncio.run(scenario()) == "skip":
        pytest.skip("Falta el esquema; corre `task up` y `task db-upgrade`")


def test_endpoints_require_authentication() -> None:
    async def scenario() -> str:
        try:
            if not await _schema_ready():
                return "skip"
            async with _client() as client:
                assert (await client.get("/api/v1/workspaces")).status_code == 401
                create = await client.post("/api/v1/workspaces", json={"name": "X"})
                assert create.status_code == 401
            return "ok"
        finally:
            await app_engine.dispose()

    if asyncio.run(scenario()) == "skip":
        pytest.skip("Falta el esquema; corre `task up` y `task db-upgrade`")
