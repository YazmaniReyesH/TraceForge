"""Utilidades compartidas por las pruebas de endpoints (contra la base real).

Patrón: cada prueba corre en su propio event loop (``asyncio.run`` vía ``run_db_test``), que
dispone el engine al final y omite la prueba si falta el esquema. La limpieza de datos la hace
cada escenario en su propio ``finally`` (borra workspaces -> cascada a membresías/proyectos- y
luego los usuarios), para ser robusto ante fallos y ante una BD no vacía.
"""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, text

from app.core.db import AsyncSessionLocal
from app.core.db import engine as app_engine
from app.main import app
from app.models import User, Workspace, WorkspaceMembership

PW = "Sup3r-Secret-Pw!"


async def schema_ready() -> bool:
    try:
        async with app_engine.connect() as conn:
            await conn.execute(text("SELECT 1 FROM user_credentials LIMIT 1"))
    except Exception:
        return False
    return True


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4()}@example.com"


@asynccontextmanager
async def client() -> AsyncIterator[AsyncClient]:
    """Cliente ASGI con jar de cookies (persiste la cookie de sesión)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def register_login(c: AsyncClient, email: str) -> UUID:
    """Registra e inicia sesión; devuelve el user_id. Deja la cookie en el jar del cliente."""
    reg = await c.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PW, "display_name": "U"},
    )
    assert reg.status_code == 201, reg.text
    user_id = UUID(reg.json()["user_id"])
    login = await c.post("/api/v1/auth/login", json={"email": email, "password": PW})
    assert login.status_code == 200, login.text
    return user_id


async def cleanup(emails: list[str]) -> None:
    """Borra los workspaces de esos usuarios (cascada) y luego los usuarios."""
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


def run_db_test(scenario: Callable[[], Awaitable[None]]) -> None:
    """Ejecuta un escenario async contra la BD; omite si falta el esquema; dispone el engine."""

    async def _wrap() -> bool:
        try:
            if not await schema_ready():
                return False
            await scenario()
            return True
        finally:
            await app_engine.dispose()

    if not asyncio.run(_wrap()):
        pytest.skip("Falta el esquema; corre `task up` y `task db-upgrade`")
