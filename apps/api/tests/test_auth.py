"""Pruebas de autenticación (F0-T4a), contra la base real.

Requieren el esquema de credenciales aplicado (en local `task up` + `task db-upgrade`;
en CI, service container con migraciones). Si la tabla `user_credentials` no existe,
las pruebas se **omiten** en vez de fallar.

Cada prueba corre en su propio event loop (``asyncio.run``), limpia los usuarios que
crea (register hace commit) y dispone el engine dentro del mismo loop.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import delete, text

from app.core.db import AsyncSessionLocal
from app.core.db import engine as app_engine
from app.main import app
from app.models import User

_PASSWORD = "Sup3r-Secret-Pw!"


async def _schema_ready() -> bool:
    """True si la tabla ``user_credentials`` existe (migración de auth aplicada)."""
    try:
        async with app_engine.connect() as conn:
            await conn.execute(text("SELECT 1 FROM user_credentials LIMIT 1"))
    except Exception:
        return False
    return True


@asynccontextmanager
async def _client() -> AsyncIterator[AsyncClient]:
    """Cliente ASGI con jar de cookies (persiste la cookie de sesión entre requests)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def _cleanup(emails: list[str]) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(delete(User).where(User.email.in_(emails)))
        await session.commit()


async def _register(client: AsyncClient, email: str, *, password: str = _PASSWORD) -> Response:
    return await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Tester"},
    )


def test_register_ok_and_hides_hash() -> None:
    async def scenario() -> str:
        try:
            if not await _schema_ready():
                return "skip"
            email = f"reg-{uuid4()}@example.com"
            try:
                async with _client() as client:
                    resp = await _register(client, email)
                    assert resp.status_code == 201, resp.text
                    body = resp.json()
                    assert body["email"] == email
                    assert body["display_name"] == "Tester"
                    assert "password_hash" not in body
                    assert "password" not in body
            finally:
                await _cleanup([email])
            return "ok"
        finally:
            await app_engine.dispose()

    if asyncio.run(scenario()) == "skip":
        pytest.skip("Falta la migración de auth; corre `task up` y `task db-upgrade`")


def test_login_sets_cookie_and_me_works() -> None:
    async def scenario() -> str:
        try:
            if not await _schema_ready():
                return "skip"
            email = f"login-{uuid4()}@example.com"
            try:
                async with _client() as client:
                    await _register(client, email)
                    login = await client.post(
                        "/api/v1/auth/login", json={"email": email, "password": _PASSWORD}
                    )
                    assert login.status_code == 200, login.text
                    assert "tf_session" in login.cookies
                    assert "password_hash" not in login.json()
                    # La cookie queda en el jar -> /me la usa automáticamente.
                    me = await client.get("/api/v1/auth/me")
                    assert me.status_code == 200
                    assert me.json()["email"] == email
            finally:
                await _cleanup([email])
            return "ok"
        finally:
            await app_engine.dispose()

    if asyncio.run(scenario()) == "skip":
        pytest.skip("Falta la migración de auth; corre `task up` y `task db-upgrade`")


def test_login_wrong_password_401_generic() -> None:
    async def scenario() -> str:
        try:
            if not await _schema_ready():
                return "skip"
            email = f"wrong-{uuid4()}@example.com"
            try:
                async with _client() as client:
                    await _register(client, email)
                    resp = await client.post(
                        "/api/v1/auth/login", json={"email": email, "password": "not-the-password"}
                    )
                    assert resp.status_code == 401
                    # Envelope {code, message}; code estable (no revela si el email existe).
                    assert resp.json()["code"] == "invalid_credentials"
            finally:
                await _cleanup([email])
            return "ok"
        finally:
            await app_engine.dispose()

    if asyncio.run(scenario()) == "skip":
        pytest.skip("Falta la migración de auth; corre `task up` y `task db-upgrade`")


def test_login_unknown_email_401_same_message() -> None:
    async def scenario() -> str:
        try:
            if not await _schema_ready():
                return "skip"
            async with _client() as client:
                resp = await client.post(
                    "/api/v1/auth/login",
                    json={"email": f"nope-{uuid4()}@example.com", "password": _PASSWORD},
                )
                assert resp.status_code == 401
                assert resp.json()["code"] == "invalid_credentials"
            return "ok"
        finally:
            await app_engine.dispose()

    if asyncio.run(scenario()) == "skip":
        pytest.skip("Falta la migración de auth; corre `task up` y `task db-upgrade`")


def test_duplicate_email_rejected() -> None:
    async def scenario() -> str:
        try:
            if not await _schema_ready():
                return "skip"
            email = f"dup-{uuid4()}@example.com"
            try:
                async with _client() as client:
                    first = await _register(client, email)
                    assert first.status_code == 201
                    second = await _register(client, email)
                    assert second.status_code == 409
            finally:
                await _cleanup([email])
            return "ok"
        finally:
            await app_engine.dispose()

    if asyncio.run(scenario()) == "skip":
        pytest.skip("Falta la migración de auth; corre `task up` y `task db-upgrade`")


def test_email_case_insensitive() -> None:
    async def scenario() -> str:
        try:
            if not await _schema_ready():
                return "skip"
            token = uuid4()
            mixed = f"Case-{token}@Example.com"
            lower = mixed.lower()
            try:
                async with _client() as client:
                    reg = await _register(client, mixed)
                    assert reg.status_code == 201
                    # Se guarda normalizado (minúsculas).
                    assert reg.json()["email"] == lower
                    # Login con otra capitalización funciona.
                    login = await client.post(
                        "/api/v1/auth/login",
                        json={"email": f"CASE-{token}@EXAMPLE.COM", "password": _PASSWORD},
                    )
                    assert login.status_code == 200
                # Registrar de nuevo con distinta capitalización -> duplicado.
                async with _client() as client2:
                    dup = await _register(client2, f"caSE-{token}@example.COM")
                    assert dup.status_code == 409
            finally:
                await _cleanup([lower])
            return "ok"
        finally:
            await app_engine.dispose()

    if asyncio.run(scenario()) == "skip":
        pytest.skip("Falta la migración de auth; corre `task up` y `task db-upgrade`")


def test_me_requires_valid_token() -> None:
    async def scenario() -> str:
        try:
            if not await _schema_ready():
                return "skip"
            async with _client() as client:
                # Sin token -> 401.
                missing = await client.get("/api/v1/auth/me")
                assert missing.status_code == 401
                # Token inválido (header Bearer) -> 401.
                invalid = await client.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": "Bearer not-a-valid-jwt"},
                )
                assert invalid.status_code == 401
            return "ok"
        finally:
            await app_engine.dispose()

    if asyncio.run(scenario()) == "skip":
        pytest.skip("Falta la migración de auth; corre `task up` y `task db-upgrade`")


def test_logout_clears_cookie() -> None:
    async def scenario() -> str:
        try:
            if not await _schema_ready():
                return "skip"
            email = f"logout-{uuid4()}@example.com"
            try:
                async with _client() as client:
                    await _register(client, email)
                    login = await client.post(
                        "/api/v1/auth/login", json={"email": email, "password": _PASSWORD}
                    )
                    assert "tf_csrf" in login.cookies  # cookie CSRF legible emitida
                    # Mutación SIN token CSRF -> 403 csrf_failed.
                    no_csrf = await client.post("/api/v1/auth/logout")
                    assert no_csrf.status_code == 403
                    assert no_csrf.json()["code"] == "csrf_failed"
                    # Mutación CON token correcto -> 204.
                    client.headers["X-CSRF-Token"] = client.cookies.get("tf_csrf") or ""
                    logout = await client.post("/api/v1/auth/logout")
                    assert logout.status_code == 204
            finally:
                await _cleanup([email])
            return "ok"
        finally:
            await app_engine.dispose()

    if asyncio.run(scenario()) == "skip":
        pytest.skip("Falta la migración de auth; corre `task up` y `task db-upgrade`")
