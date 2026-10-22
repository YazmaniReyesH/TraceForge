"""Prueba del invariante de borrado seguro de usuario (servicio, sin endpoint de baja)."""

import pytest

from app.core.db import AsyncSessionLocal
from app.users.errors import UserHasMembershipsError
from app.users.repository import UserAccountRepository
from app.users.service import UserService
from tests._helpers import cleanup, client, register_login, run_db_test, unique_email


def test_user_with_memberships_cannot_be_deleted() -> None:
    async def scenario() -> None:
        email = unique_email("del-m")
        try:
            async with client() as c:
                uid = await register_login(c, email)
                # Crear un workspace deja al usuario como owner (tiene membresía).
                await c.post("/api/v1/workspaces", json={"name": "W"})
            async with AsyncSessionLocal() as s:
                service = UserService(UserAccountRepository(s), s)
                with pytest.raises(UserHasMembershipsError):
                    await service.delete_user(uid)
        finally:
            await cleanup([email])

    run_db_test(scenario)


def test_user_without_memberships_can_be_deleted() -> None:
    async def scenario() -> None:
        email = unique_email("del-n")
        deleted = False
        try:
            async with client() as c:
                uid = await register_login(c, email)
            async with AsyncSessionLocal() as s:
                service = UserService(UserAccountRepository(s), s)
                await service.delete_user(uid)
                deleted = True
            async with AsyncSessionLocal() as s2:
                assert await UserAccountRepository(s2).get_by_id(uid) is None
        finally:
            if not deleted:
                await cleanup([email])

    run_db_test(scenario)
