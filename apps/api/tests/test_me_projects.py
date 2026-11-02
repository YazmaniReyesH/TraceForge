"""Pruebas de GET /api/v1/me/projects (vista transversal por usuario, F0-T5b)."""

from tests._helpers import cleanup, client, register_login, run_db_test, unique_email


def test_me_projects_by_role() -> None:
    async def scenario() -> None:
        owner = unique_email("me-o")
        member_b = unique_email("me-b")
        member_c = unique_email("me-c")
        guest = unique_email("me-g")
        foreign = unique_email("me-d")
        try:
            async with (
                client() as ca,
                client() as cb,
                client() as cc,
                client() as cg,
                client() as cd,
            ):
                await register_login(ca, owner)
                await register_login(cb, member_b)
                await register_login(cc, member_c)
                await register_login(cg, guest)
                await register_login(cd, foreign)

                # A: workspace W1 con dos proyectos.
                wid = (await ca.post("/api/v1/workspaces", json={"name": "W1"})).json()[
                    "workspace_id"
                ]
                base = f"/api/v1/workspaces/{wid}/projects"
                p1 = (await ca.post(base, json={"name": "P1"})).json()["project_id"]
                p2 = (await ca.post(base, json={"name": "P2"})).json()["project_id"]

                # Membresías de workspace.
                m = f"/api/v1/workspaces/{wid}/members"
                await ca.post(m, json={"email": member_b, "role": "member"})
                await ca.post(m, json={"email": member_c, "role": "member"})
                await ca.post(m, json={"email": guest, "role": "guest"})
                # Membresías de proyecto: B viewer de P1; G viewer de P2; C sin ninguna.
                await ca.post(f"{base}/{p1}/members", json={"email": member_b, "role": "viewer"})
                await ca.post(f"{base}/{p2}/members", json={"email": guest, "role": "viewer"})

                # D: workspace ajeno con un proyecto (no debe aparecer en la lista de A).
                wid2 = (await cd.post("/api/v1/workspaces", json={"name": "W2"})).json()[
                    "workspace_id"
                ]
                await cd.post(f"/api/v1/workspaces/{wid2}/projects", json={"name": "PX"})

                # Owner: ve P1 y P2 con rol efectivo lead y workspace_name correcto.
                a_list = (await ca.get("/api/v1/me/projects")).json()
                assert {p["name"] for p in a_list} == {"P1", "P2"}
                assert all(p["role"] == "lead" for p in a_list)
                assert all(p["workspace_name"] == "W1" for p in a_list)
                assert all(p["workspace_id"] == wid for p in a_list)

                # Member B: solo P1 (viewer).
                b_list = (await cb.get("/api/v1/me/projects")).json()
                assert [(p["name"], p["role"]) for p in b_list] == [("P1", "viewer")]

                # Member C sin membresía de proyecto: ninguno.
                assert (await cc.get("/api/v1/me/projects")).json() == []

                # Guest G: solo P2 (viewer), no el otro proyecto del mismo workspace.
                g_list = (await cg.get("/api/v1/me/projects")).json()
                assert [(p["name"], p["role"]) for p in g_list] == [("P2", "viewer")]
        finally:
            await cleanup([owner, member_b, member_c, guest, foreign])

    run_db_test(scenario)


def test_me_projects_requires_auth() -> None:
    async def scenario() -> None:
        async with client() as c:
            resp = await c.get("/api/v1/me/projects")
            assert resp.status_code == 401
            assert resp.json()["code"] == "unauthenticated"

    run_db_test(scenario)
