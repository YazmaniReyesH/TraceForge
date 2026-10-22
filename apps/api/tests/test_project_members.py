"""Pruebas de membresías de proyecto: regla dura guest=viewer y rol efectivo."""

from tests._helpers import cleanup, client, register_login, run_db_test, unique_email


def test_guest_must_be_viewer_is_enforced() -> None:
    async def scenario() -> None:
        owner = unique_email("pm-o")
        guest = unique_email("pm-g")
        try:
            async with client() as co, client() as cg:
                await register_login(co, owner)
                g_id = await register_login(cg, guest)
                wid = (await co.post("/api/v1/workspaces", json={"name": "W"})).json()[
                    "workspace_id"
                ]
                base = f"/api/v1/workspaces/{wid}/projects"
                pid = (await co.post(base, json={"name": "P"})).json()["project_id"]
                # El guest es miembro de workspace con rol guest.
                await co.post(
                    f"/api/v1/workspaces/{wid}/members", json={"email": guest, "role": "guest"}
                )
                members = f"{base}/{pid}/members"
                # guest + contributor -> rechazado (regla dura, 422).
                bad = await co.post(members, json={"email": guest, "role": "contributor"})
                assert bad.status_code == 422, bad.text
                # guest + viewer -> permitido.
                ok = await co.post(members, json={"email": guest, "role": "viewer"})
                assert ok.status_code == 201, ok.text
                # Cambiar a contributor tampoco se permite.
                chg = await co.patch(f"{members}/{g_id}", json={"role": "contributor"})
                assert chg.status_code == 422
        finally:
            await cleanup([owner, guest])

    run_db_test(scenario)


def test_contributor_can_update_project() -> None:
    async def scenario() -> None:
        owner = unique_email("pm2-o")
        contributor = unique_email("pm2-c")
        try:
            async with client() as co, client() as cc:
                await register_login(co, owner)
                await register_login(cc, contributor)
                wid = (await co.post("/api/v1/workspaces", json={"name": "W"})).json()[
                    "workspace_id"
                ]
                base = f"/api/v1/workspaces/{wid}/projects"
                pid = (await co.post(base, json={"name": "P"})).json()["project_id"]
                await co.post(
                    f"/api/v1/workspaces/{wid}/members",
                    json={"email": contributor, "role": "member"},
                )
                await co.post(
                    f"{base}/{pid}/members", json={"email": contributor, "role": "contributor"}
                )
                resp = await cc.patch(f"{base}/{pid}", json={"name": "editado"})
                assert resp.status_code == 200, resp.text
                assert resp.json()["name"] == "editado"
        finally:
            await cleanup([owner, contributor])

    run_db_test(scenario)


def test_project_member_must_be_workspace_member() -> None:
    async def scenario() -> None:
        owner = unique_email("pm3-o")
        outsider = unique_email("pm3-x")
        try:
            async with client() as co, client() as cx:
                await register_login(co, owner)
                await register_login(cx, outsider)  # existe, pero no es miembro del workspace
                wid = (await co.post("/api/v1/workspaces", json={"name": "W"})).json()[
                    "workspace_id"
                ]
                base = f"/api/v1/workspaces/{wid}/projects"
                pid = (await co.post(base, json={"name": "P"})).json()["project_id"]
                resp = await co.post(
                    f"{base}/{pid}/members", json={"email": outsider, "role": "viewer"}
                )
                assert resp.status_code == 422, resp.text  # no es miembro del workspace
        finally:
            await cleanup([owner, outsider])

    run_db_test(scenario)
