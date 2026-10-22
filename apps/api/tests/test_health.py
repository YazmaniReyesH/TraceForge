"""Pruebas de los endpoints de salud: liveness y readiness.

Las pruebas de readiness son async y cada una corre en su propio event loop
(``asyncio.run``). El engine async de la app cachea conexiones asyncpg ligadas al
loop donde se crearon, así que cada prueba que lo usa lo **dispone dentro de su
mismo loop** para no arrastrar conexiones entre loops.
"""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.db import database_ready, get_engine
from app.core.db import engine as app_engine
from app.main import app


async def _get(path: str) -> tuple[int, dict[str, object]]:
    """Hace un GET contra la app vía ASGI y devuelve (status, json)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(path)
    return response.status_code, response.json()


def test_health_liveness_ok() -> None:
    """``GET /health`` responde 200 sin tocar la base (liveness)."""
    status, body = asyncio.run(_get("/health"))

    assert status == 200
    assert body["status"] == "ok"
    assert body["version"] == get_settings().version


def test_health_ready_ok_con_base() -> None:
    """``GET /health/ready`` responde 200 cuando la base está arriba.

    Requiere PostgreSQL en marcha (``task up``). En CI lo aporta el service
    container; en local, si la base no está accesible, la prueba se omite.
    """

    async def scenario() -> tuple[int, dict[str, object]] | None:
        try:
            if not await database_ready(app_engine):
                return None
            return await _get("/health/ready")
        finally:
            await app_engine.dispose()

    result = asyncio.run(scenario())
    if result is None:
        pytest.skip("PostgreSQL no está accesible; ejecuta `task up` para correr esta prueba")

    status, body = result
    assert status == 200
    assert body == {"status": "ready"}


def test_health_ready_503_sin_base() -> None:
    """``GET /health/ready`` responde 503 cuando la base no responde.

    Determinista: sustituye el engine por uno que apunta a un puerto cerrado.
    """

    async def scenario() -> tuple[int, dict[str, object]]:
        bad_engine = create_async_engine(
            "postgresql+asyncpg://tf:tf@127.0.0.1:1/traceforge",
            pool_pre_ping=True,
        )
        app.dependency_overrides[get_engine] = lambda: bad_engine
        try:
            return await _get("/health/ready")
        finally:
            app.dependency_overrides.pop(get_engine, None)
            await bad_engine.dispose()

    status, body = asyncio.run(scenario())
    assert status == 503
    assert body == {"status": "not ready"}
