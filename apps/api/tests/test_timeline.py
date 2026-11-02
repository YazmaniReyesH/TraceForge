"""Pruebas del timeline (F1-T1): sesiones e ítems de evidencia append-only.

Cubre: alta de sesión/ítems y orden cronológico (por posición), cómputo y estabilidad del hash,
"editar" = versión nueva que conserva el historial, soft-delete (no borrado físico), aislamiento
por proyecto (404) y permisos (viewer no escribe -> 403). Los escenarios contra la BD usan el
patrón ``run_db_test`` (omiten si falta el esquema).
"""

from uuid import UUID

from httpx import AsyncClient
from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.models import EvidenceItem
from app.models.enums import EvidenceKind
from app.timeline.hashing import compute_content_hash
from tests._helpers import cleanup, client, register_login, run_db_test, unique_email

# ── Hashing (unitario, sin BD) ──


def test_hash_is_stable_and_ignores_presentation_hints() -> None:
    """Mismo contenido -> mismo hash; ``tool``/``language`` no forman parte del hash."""
    h1 = compute_content_hash(
        EvidenceKind.COMMAND, command_text="nmap -sV host", command_output="22/tcp open"
    )
    h2 = compute_content_hash(
        EvidenceKind.COMMAND, command_text="nmap -sV host", command_output="22/tcp open"
    )
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 en hex
    # Distinto contenido -> distinto hash.
    h3 = compute_content_hash(
        EvidenceKind.COMMAND, command_text="nmap -sV host", command_output="otra salida"
    )
    assert h3 != h1
    # command vs note con texto "igual" no colisionan (el kind entra en el objeto canónico).
    assert compute_content_hash(EvidenceKind.NOTE, note_text="hola") != compute_content_hash(
        EvidenceKind.COMMAND, command_text="hola"
    )


# ── Helpers de escenario ──


async def _owner_project(c: AsyncClient) -> str:
    """Crea workspace + project para el owner; devuelve la URL base de sesiones del project."""
    wid = (await c.post("/api/v1/workspaces", json={"name": "W"})).json()["workspace_id"]
    base = f"/api/v1/workspaces/{wid}/projects"
    pid = (await c.post(base, json={"name": "P"})).json()["project_id"]
    return f"{base}/{pid}/sessions"


# ── Sesiones e ítems (contra la BD) ──


def test_create_session_and_items_in_order() -> None:
    async def scenario() -> None:
        email = unique_email("tl-order")
        try:
            async with client() as c:
                await register_login(c, email)
                sessions = await _owner_project(c)
                sid = (await c.post(sessions, json={"name": "Recon"})).json()["session_id"]
                items = f"{sessions}/{sid}/items"
                first = await c.post(items, json={"kind": "command", "command_text": "whoami"})
                assert first.status_code == 201, first.text
                body = first.json()
                assert body["kind"] == "command"
                assert body["position"] == 0
                assert body["current_version"] == 1
                assert body["current"]["content_hash"]  # hash calculado por el backend
                await c.post(items, json={"kind": "note", "note_text": "segunda"})
                await c.post(items, json={"kind": "command", "command_text": "id"})
                listing = (await c.get(items)).json()
                # Orden cronológico estable por posición de inserción.
                assert [i["position"] for i in listing] == [0, 1, 2]
                assert [
                    i["current"]["command_text"] or i["current"]["note_text"] for i in listing
                ] == [
                    "whoami",
                    "segunda",
                    "id",
                ]
        finally:
            await cleanup([email])

    run_db_test(scenario, requires="sessions")


def test_hash_matches_canonical_recompute() -> None:
    """El hash devuelto por el API coincide con el recomputado por la regla canónica."""

    async def scenario() -> None:
        email = unique_email("tl-hash")
        try:
            async with client() as c:
                await register_login(c, email)
                sessions = await _owner_project(c)
                sid = (await c.post(sessions, json={"name": "S"})).json()["session_id"]
                created = await c.post(
                    f"{sessions}/{sid}/items",
                    json={
                        "kind": "command",
                        "command_text": "cat /etc/passwd",
                        "command_output": "root:x:0:0",
                        "tool": "bash",  # pista de presentación: NO entra en el hash
                    },
                )
                api_hash = created.json()["current"]["content_hash"]
                expected = compute_content_hash(
                    EvidenceKind.COMMAND,
                    command_text="cat /etc/passwd",
                    command_output="root:x:0:0",
                )
                assert api_hash == expected
        finally:
            await cleanup([email])

    run_db_test(scenario, requires="sessions")


def test_edit_creates_new_version_and_preserves_history() -> None:
    async def scenario() -> None:
        email = unique_email("tl-edit")
        try:
            async with client() as c:
                await register_login(c, email)
                sessions = await _owner_project(c)
                sid = (await c.post(sessions, json={"name": "S"})).json()["session_id"]
                items = f"{sessions}/{sid}/items"
                created = (await c.post(items, json={"kind": "note", "note_text": "v1"})).json()
                iid = created["evidence_item_id"]
                v1_hash = created["current"]["content_hash"]
                # "Editar" = versión nueva (append-only).
                edited = await c.patch(
                    f"{items}/{iid}", json={"kind": "note", "note_text": "v2 corregida"}
                )
                assert edited.status_code == 200, edited.text
                assert edited.json()["current_version"] == 2
                assert edited.json()["current"]["note_text"] == "v2 corregida"
                assert edited.json()["current"]["content_hash"] != v1_hash
                # El historial conserva la v1 con su hash original.
                detail = (await c.get(f"{items}/{iid}?include_history=true")).json()
                hist = detail["history"]
                assert [v["version"] for v in hist] == [1, 2]
                assert hist[0]["note_text"] == "v1"
                assert hist[0]["content_hash"] == v1_hash
        finally:
            await cleanup([email])

    run_db_test(scenario, requires="sessions")


def test_edit_cannot_change_kind() -> None:
    async def scenario() -> None:
        email = unique_email("tl-kind")
        try:
            async with client() as c:
                await register_login(c, email)
                sessions = await _owner_project(c)
                sid = (await c.post(sessions, json={"name": "S"})).json()["session_id"]
                items = f"{sessions}/{sid}/items"
                iid = (await c.post(items, json={"kind": "note", "note_text": "n"})).json()[
                    "evidence_item_id"
                ]
                resp = await c.patch(
                    f"{items}/{iid}", json={"kind": "command", "command_text": "x"}
                )
                assert resp.status_code == 409, resp.text
                assert resp.json()["code"] == "evidence_kind_mismatch"
        finally:
            await cleanup([email])

    run_db_test(scenario, requires="sessions")


def test_soft_delete_hides_item_but_is_not_physical() -> None:
    async def scenario() -> None:
        email = unique_email("tl-del")
        try:
            async with client() as c:
                await register_login(c, email)
                sessions = await _owner_project(c)
                sid = (await c.post(sessions, json={"name": "S"})).json()["session_id"]
                items = f"{sessions}/{sid}/items"
                iid = (await c.post(items, json={"kind": "note", "note_text": "n"})).json()[
                    "evidence_item_id"
                ]
                assert (await c.delete(f"{items}/{iid}")).status_code == 204
                # Deja de verse (lista y detalle), pero la fila no se borra físicamente.
                assert (await c.get(f"{items}/{iid}")).status_code == 404
                assert (await c.get(items)).json() == []
                # Verificación directa en BD: la fila sigue existiendo con deleted_at.
                async with AsyncSessionLocal() as s:
                    row = (
                        await s.execute(
                            select(EvidenceItem).where(EvidenceItem.evidence_item_id == UUID(iid))
                        )
                    ).scalar_one()
                    assert row.deleted_at is not None  # soft-delete, no DELETE físico
        finally:
            await cleanup([email])

    run_db_test(scenario, requires="sessions")


def test_timeline_is_isolated_by_project() -> None:
    async def scenario() -> None:
        email = unique_email("tl-iso")
        try:
            async with client() as c:
                await register_login(c, email)
                wid = (await c.post("/api/v1/workspaces", json={"name": "W"})).json()[
                    "workspace_id"
                ]
                base = f"/api/v1/workspaces/{wid}/projects"
                pa = (await c.post(base, json={"name": "A"})).json()["project_id"]
                pb = (await c.post(base, json={"name": "B"})).json()["project_id"]
                sa = f"{base}/{pa}/sessions"
                sid = (await c.post(sa, json={"name": "S-A"})).json()["session_id"]
                # La sesión de A no es visible bajo el proyecto B (ruta cruzada) -> 404.
                cross = f"{base}/{pb}/sessions/{sid}"
                assert (await c.get(f"{cross}/items")).status_code == 404
                assert (await c.patch(cross, json={"name": "x"})).status_code == 404
        finally:
            await cleanup([email])

    run_db_test(scenario, requires="sessions")


def test_viewer_can_read_but_not_write_evidence() -> None:
    async def scenario() -> None:
        owner = unique_email("tl-v-o")
        viewer = unique_email("tl-v-b")
        try:
            async with client() as co, client() as cb:
                await register_login(co, owner)
                await register_login(cb, viewer)
                wid = (await co.post("/api/v1/workspaces", json={"name": "W"})).json()[
                    "workspace_id"
                ]
                base = f"/api/v1/workspaces/{wid}/projects"
                pid = (await co.post(base, json={"name": "P"})).json()["project_id"]
                sessions = f"{base}/{pid}/sessions"
                sid = (await co.post(sessions, json={"name": "S"})).json()["session_id"]
                items = f"{sessions}/{sid}/items"
                await co.post(
                    f"/api/v1/workspaces/{wid}/members", json={"email": viewer, "role": "member"}
                )
                await co.post(f"{base}/{pid}/members", json={"email": viewer, "role": "viewer"})
                # Viewer lee...
                assert (await cb.get(items)).status_code == 200
                # ...pero no escribe (projects:update -> contributor/lead).
                denied = await cb.post(items, json={"kind": "note", "note_text": "x"})
                assert denied.status_code == 403, denied.text
                assert (await cb.post(sessions, json={"name": "nope"})).status_code == 403
        finally:
            await cleanup([owner, viewer])

    run_db_test(scenario, requires="sessions")
