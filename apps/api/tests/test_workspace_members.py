"""Pruebas de membresías de workspace e invariantes de owner."""

from uuid import UUID

from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.models import WorkspaceMembership
from app.models.enums import WorkspaceRole
from tests._helpers import cleanup, client, register_login, run_db_test, unique_email


async def _role_in_db(workspace_id: str, user_id: UUID) -> WorkspaceRole | None:
    async with AsyncSessionLocal() as s:
        return (
            await s.execute(
                select(WorkspaceMembership.role).where(
                    WorkspaceMembership.workspace_id == UUID(workspace_id),
                    WorkspaceMembership.user_id == user_id,
                )
            )
        ).scalar_one_or_none()


def test_add_change_remove_member() -> None:
    async def scenario() -> None:
        owner = unique_email("wm-o")
        member = unique_email("wm-b")
        try:
            async with client() as co, client() as cb:
                await register_login(co, owner)
                b_id = await register_login(cb, member)
                wid = (await co.post("/api/v1/workspaces", json={"name": "W"})).json()[
                    "workspace_id"
                ]
                m = f"/api/v1/workspaces/{wid}/members"
                add = await co.post(m, json={"email": member, "role": "member"})
                assert add.status_code == 201, add.text
                emails = {row["email"] for row in (await co.get(m)).json()}
                assert member in emails
                chg = await co.patch(f"{m}/{b_id}", json={"role": "admin"})
                assert chg.status_code == 200
                assert chg.json()["role"] == "admin"
                assert (await co.delete(f"{m}/{b_id}")).status_code == 204
                assert member not in {row["email"] for row in (await co.get(m)).json()}
        finally:
            await cleanup([owner, member])

    run_db_test(scenario)


def test_cannot_add_owner_role() -> None:
    async def scenario() -> None:
        owner = unique_email("wm2-o")
        other = unique_email("wm2-b")
        try:
            async with client() as co, client() as cb:
                await register_login(co, owner)
                await register_login(cb, other)
                wid = (await co.post("/api/v1/workspaces", json={"name": "W"})).json()[
                    "workspace_id"
                ]
                resp = await co.post(
                    f"/api/v1/workspaces/{wid}/members", json={"email": other, "role": "owner"}
                )
                assert resp.status_code == 409  # owner solo por transferencia
        finally:
            await cleanup([owner, other])

    run_db_test(scenario)


def test_cannot_degrade_or_remove_sole_owner() -> None:
    async def scenario() -> None:
        owner = unique_email("wm3-o")
        try:
            async with client() as co:
                o_id = await register_login(co, owner)
                wid = (await co.post("/api/v1/workspaces", json={"name": "W"})).json()[
                    "workspace_id"
                ]
                m = f"/api/v1/workspaces/{wid}/members"
                assert (await co.patch(f"{m}/{o_id}", json={"role": "admin"})).status_code == 409
                assert (await co.delete(f"{m}/{o_id}")).status_code == 409
                # Sigue siendo owner.
                assert await _role_in_db(wid, o_id) == WorkspaceRole.OWNER
        finally:
            await cleanup([owner])

    run_db_test(scenario)


def test_transfer_ownership_is_atomic() -> None:
    async def scenario() -> None:
        owner = unique_email("wm4-o")
        heir = unique_email("wm4-b")
        try:
            async with client() as co, client() as cb:
                o_id = await register_login(co, owner)
                b_id = await register_login(cb, heir)
                wid = (await co.post("/api/v1/workspaces", json={"name": "W"})).json()[
                    "workspace_id"
                ]
                await co.post(
                    f"/api/v1/workspaces/{wid}/members", json={"email": heir, "role": "member"}
                )
                tr = await co.post(
                    f"/api/v1/workspaces/{wid}/transfer-ownership",
                    json={"new_owner_user_id": str(b_id)},
                )
                assert tr.status_code == 204, tr.text
                # Nuevo owner sube; anterior baja a admin (exactamente un owner).
                assert await _role_in_db(wid, b_id) == WorkspaceRole.OWNER
                assert await _role_in_db(wid, o_id) == WorkspaceRole.ADMIN
        finally:
            await cleanup([owner, heir])

    run_db_test(scenario)


def test_transfer_requires_owner_role() -> None:
    async def scenario() -> None:
        owner = unique_email("wm5-o")
        admin = unique_email("wm5-a")
        try:
            async with client() as co, client() as ca:
                await register_login(co, owner)
                a_id = await register_login(ca, admin)
                wid = (await co.post("/api/v1/workspaces", json={"name": "W"})).json()[
                    "workspace_id"
                ]
                await co.post(
                    f"/api/v1/workspaces/{wid}/members", json={"email": admin, "role": "admin"}
                )
                # Un admin no puede transferir la propiedad (403).
                resp = await ca.post(
                    f"/api/v1/workspaces/{wid}/transfer-ownership",
                    json={"new_owner_user_id": str(a_id)},
                )
                assert resp.status_code == 403
        finally:
            await cleanup([owner, admin])

    run_db_test(scenario)
