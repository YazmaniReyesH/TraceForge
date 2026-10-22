"""Pruebas de CRUD de projects, aislamiento y gate de proyecto (404/403)."""

from tests._helpers import cleanup, client, register_login, run_db_test, unique_email


def test_project_crud_by_owner() -> None:
    async def scenario() -> None:
        email = unique_email("proj-owner")
        try:
            async with client() as c:
                await register_login(c, email)
                ws = (await c.post("/api/v1/workspaces", json={"name": "W"})).json()
                base = f"/api/v1/workspaces/{ws['workspace_id']}/projects"
                created = await c.post(base, json={"name": "P1", "classification": "conf"})
                assert created.status_code == 201, created.text
                body = created.json()
                assert body["name"] == "P1"
                assert body["classification"] == "conf"
                assert body["ai_policy"] is None
                pid = body["project_id"]
                assert (await c.get(f"{base}/{pid}")).status_code == 200
                patched = await c.patch(f"{base}/{pid}", json={"name": "P1-edit"})
                assert patched.status_code == 200
                assert patched.json()["name"] == "P1-edit"
                listing = await c.get(base)
                assert [p["name"] for p in listing.json()] == ["P1-edit"]
                assert (await c.delete(f"{base}/{pid}")).status_code == 204
                assert (await c.get(f"{base}/{pid}")).status_code == 404
        finally:
            await cleanup([email])

    run_db_test(scenario)


def test_project_access_isolated_to_workspace_members() -> None:
    async def scenario() -> None:
        owner = unique_email("proj-iso-o")
        outsider = unique_email("proj-iso-x")
        try:
            async with client() as co, client() as cx:
                await register_login(co, owner)
                await register_login(cx, outsider)
                ws = (await co.post("/api/v1/workspaces", json={"name": "W"})).json()
                base = f"/api/v1/workspaces/{ws['workspace_id']}/projects"
                proj = (await co.post(base, json={"name": "P"})).json()
                # El de fuera no es miembro del workspace -> 404 (no revela el proyecto).
                assert (await cx.get(f"{base}/{proj['project_id']}")).status_code == 404
                assert (await cx.get(base)).status_code == 404
        finally:
            await cleanup([owner, outsider])

    run_db_test(scenario)


def test_member_sees_only_projects_with_membership() -> None:
    async def scenario() -> None:
        owner = unique_email("proj-m-o")
        member = unique_email("proj-m-b")
        try:
            async with client() as co, client() as cb:
                await register_login(co, owner)
                await register_login(cb, member)
                ws = (await co.post("/api/v1/workspaces", json={"name": "W"})).json()
                wid = ws["workspace_id"]
                base = f"/api/v1/workspaces/{wid}/projects"
                p1 = (await co.post(base, json={"name": "P1"})).json()
                p2 = (await co.post(base, json={"name": "P2"})).json()
                # B es member del workspace, miembro de P1 (viewer), no de P2.
                await co.post(
                    f"/api/v1/workspaces/{wid}/members", json={"email": member, "role": "member"}
                )
                add = await co.post(
                    f"{base}/{p1['project_id']}/members", json={"email": member, "role": "viewer"}
                )
                assert add.status_code == 201, add.text
                # B solo ve P1; P2 le da 404.
                listing = await cb.get(base)
                assert [p["name"] for p in listing.json()] == ["P1"]
                assert (await cb.get(f"{base}/{p1['project_id']}")).status_code == 200
                assert (await cb.get(f"{base}/{p2['project_id']}")).status_code == 404
        finally:
            await cleanup([owner, member])

    run_db_test(scenario)


def test_viewer_can_read_but_not_modify_project() -> None:
    async def scenario() -> None:
        owner = unique_email("proj-v-o")
        viewer = unique_email("proj-v-b")
        try:
            async with client() as co, client() as cb:
                await register_login(co, owner)
                await register_login(cb, viewer)
                ws = (await co.post("/api/v1/workspaces", json={"name": "W"})).json()
                wid = ws["workspace_id"]
                base = f"/api/v1/workspaces/{wid}/projects"
                proj = (await co.post(base, json={"name": "P"})).json()
                pid = proj["project_id"]
                await co.post(
                    f"/api/v1/workspaces/{wid}/members", json={"email": viewer, "role": "member"}
                )
                await co.post(f"{base}/{pid}/members", json={"email": viewer, "role": "viewer"})
                assert (await cb.get(f"{base}/{pid}")).status_code == 200  # lee
                assert (await cb.patch(f"{base}/{pid}", json={"name": "x"})).status_code == 403
                assert (await cb.delete(f"{base}/{pid}")).status_code == 403
        finally:
            await cleanup([owner, viewer])

    run_db_test(scenario)
