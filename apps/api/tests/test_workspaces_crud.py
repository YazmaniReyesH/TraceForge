"""Pruebas de editar (PATCH) y eliminar (DELETE protegido) un workspace (F0-T5b)."""

from tests._helpers import cleanup, client, register_login, run_db_test, unique_email


def test_owner_can_rename_workspace() -> None:
    async def scenario() -> None:
        owner = unique_email("wsc-o")
        try:
            async with client() as c:
                await register_login(c, owner)
                wid = (await c.post("/api/v1/workspaces", json={"name": "Antes"})).json()[
                    "workspace_id"
                ]
                resp = await c.patch(f"/api/v1/workspaces/{wid}", json={"name": "Después"})
                assert resp.status_code == 200, resp.text
                assert resp.json()["name"] == "Después"
                assert (await c.get(f"/api/v1/workspaces/{wid}")).json()["name"] == "Después"
        finally:
            await cleanup([owner])

    run_db_test(scenario)


def test_rename_forbidden_for_member() -> None:
    async def scenario() -> None:
        owner = unique_email("wsc-ro")
        member = unique_email("wsc-rm")
        try:
            async with client() as co, client() as cm:
                await register_login(co, owner)
                await register_login(cm, member)
                wid = (await co.post("/api/v1/workspaces", json={"name": "W"})).json()[
                    "workspace_id"
                ]
                await co.post(
                    f"/api/v1/workspaces/{wid}/members", json={"email": member, "role": "member"}
                )
                resp = await cm.patch(f"/api/v1/workspaces/{wid}", json={"name": "X"})
                assert resp.status_code == 403
                assert resp.json()["code"] == "forbidden"
        finally:
            await cleanup([owner, member])

    run_db_test(scenario)


def test_owner_can_delete_empty_workspace() -> None:
    async def scenario() -> None:
        owner = unique_email("wsc-d")
        try:
            async with client() as c:
                await register_login(c, owner)
                wid = (await c.post("/api/v1/workspaces", json={"name": "Vacío"})).json()[
                    "workspace_id"
                ]
                assert (await c.delete(f"/api/v1/workspaces/{wid}")).status_code == 204
                ids = [w["workspace_id"] for w in (await c.get("/api/v1/workspaces")).json()]
                assert wid not in ids
        finally:
            await cleanup([owner])

    run_db_test(scenario)


def test_delete_rejected_when_has_projects() -> None:
    async def scenario() -> None:
        owner = unique_email("wsc-dp")
        try:
            async with client() as c:
                await register_login(c, owner)
                wid = (await c.post("/api/v1/workspaces", json={"name": "W"})).json()[
                    "workspace_id"
                ]
                await c.post(f"/api/v1/workspaces/{wid}/projects", json={"name": "P"})
                resp = await c.delete(f"/api/v1/workspaces/{wid}")
                assert resp.status_code == 409
                assert resp.json()["code"] == "workspace_not_empty"
        finally:
            await cleanup([owner])

    run_db_test(scenario)


def test_delete_rejected_when_has_other_members() -> None:
    async def scenario() -> None:
        owner = unique_email("wsc-dm-o")
        member = unique_email("wsc-dm-m")
        try:
            async with client() as co, client() as cm:
                await register_login(co, owner)
                await register_login(cm, member)
                wid = (await co.post("/api/v1/workspaces", json={"name": "W"})).json()[
                    "workspace_id"
                ]
                await co.post(
                    f"/api/v1/workspaces/{wid}/members", json={"email": member, "role": "member"}
                )
                resp = await co.delete(f"/api/v1/workspaces/{wid}")
                assert resp.status_code == 409
                assert resp.json()["code"] == "workspace_not_empty"
        finally:
            await cleanup([owner, member])

    run_db_test(scenario)


def test_delete_forbidden_for_non_owner() -> None:
    async def scenario() -> None:
        owner = unique_email("wsc-da-o")
        admin = unique_email("wsc-da-a")
        try:
            async with client() as co, client() as ca:
                await register_login(co, owner)
                await register_login(ca, admin)
                wid = (await co.post("/api/v1/workspaces", json={"name": "W"})).json()[
                    "workspace_id"
                ]
                await co.post(
                    f"/api/v1/workspaces/{wid}/members", json={"email": admin, "role": "admin"}
                )
                # admin tiene workspaces:update pero NO workspaces:delete -> 403.
                resp = await ca.delete(f"/api/v1/workspaces/{wid}")
                assert resp.status_code == 403
                assert resp.json()["code"] == "forbidden"
        finally:
            await cleanup([owner, admin])

    run_db_test(scenario)
