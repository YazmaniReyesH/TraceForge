"""Pruebas del timeline (F1-T1): sesiones e ítems de evidencia append-only.

Cubre: alta de sesión/ítems y orden cronológico (por posición), cómputo y estabilidad del hash,
"editar" = versión nueva que conserva el historial, soft-delete (no borrado físico), aislamiento
por proyecto (404) y permisos (viewer no escribe -> 403). Los escenarios contra la BD usan el
patrón ``run_db_test`` (omiten si falta el esquema).
"""

from typing import Any
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.models import EvidenceItem
from app.models.enums import EvidenceKind
from app.timeline.hashing import compute_content_hash
from app.timeline.service import TimelineService
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


def test_midpoint_gap_arithmetic() -> None:
    """Aritmética de la escala con huecos (sin BD): punto medio, fin de zona y agotamiento."""
    mid = TimelineService._midpoint
    assert mid(0, 1000) == 500  # al inicio, con hueco amplio
    assert mid(1000, 2000) == 1500  # entre dos, punto medio
    assert mid(1000, None) == 2000  # al final: left + STEP
    assert mid(0, None) == 1000  # sesión vacía / insertar al final sin vecino derecho
    assert mid(0, 2) == 1  # hueco mínimo que todavía cabe
    assert mid(1000, 1001) is None  # sin entero intermedio -> hay que renumerar
    assert mid(5, 6) is None


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
                assert body["current_version"] == 1
                assert body["current"]["content_hash"]  # hash calculado por el backend
                await c.post(items, json={"kind": "note", "note_text": "segunda"})
                await c.post(items, json={"kind": "command", "command_text": "id"})
                listing = (await c.get(items)).json()
                # El append deja posiciones en escala con huecos, estrictamente crecientes.
                positions = [i["position"] for i in listing]
                assert positions == sorted(positions)
                assert len(set(positions)) == 3
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


# ── Reordenar / insertar (escala con huecos, ADR-0013) ──


def _texts(listing: list[dict[str, Any]]) -> list[str]:
    return [i["current"]["command_text"] or i["current"]["note_text"] for i in listing]


def test_insert_between_two_keeps_order_without_touching_hashes() -> None:
    async def scenario() -> None:
        email = unique_email("tl-ins")
        try:
            async with client() as c:
                await register_login(c, email)
                sessions = await _owner_project(c)
                sid = (await c.post(sessions, json={"name": "S"})).json()["session_id"]
                items = f"{sessions}/{sid}/items"
                a = (await c.post(items, json={"kind": "note", "note_text": "A"})).json()
                b = (await c.post(items, json={"kind": "note", "note_text": "B"})).json()
                # Insertar C justo después de A (entre A y B).
                created = await c.post(
                    items,
                    json={
                        "kind": "note",
                        "note_text": "C",
                        "after_item_id": a["evidence_item_id"],
                    },
                )
                assert created.status_code == 201, created.text
                listing = (await c.get(items)).json()
                assert _texts(listing) == ["A", "C", "B"]
                # Insertar entre dos NO altera el contenido/hash de los vecinos (append-only).
                by_id = {i["evidence_item_id"]: i for i in listing}
                assert (
                    by_id[a["evidence_item_id"]]["current"]["content_hash"]
                    == (a["current"]["content_hash"])
                )
                assert (
                    by_id[b["evidence_item_id"]]["current"]["content_hash"]
                    == (b["current"]["content_hash"])
                )
                assert by_id[a["evidence_item_id"]]["current_version"] == 1
                assert by_id[b["evidence_item_id"]]["current_version"] == 1
        finally:
            await cleanup([email])

    run_db_test(scenario, requires="sessions")


def test_move_item_reorders_without_new_version() -> None:
    async def scenario() -> None:
        email = unique_email("tl-move")
        try:
            async with client() as c:
                await register_login(c, email)
                sessions = await _owner_project(c)
                sid = (await c.post(sessions, json={"name": "S"})).json()["session_id"]
                items = f"{sessions}/{sid}/items"
                a = (await c.post(items, json={"kind": "note", "note_text": "A"})).json()
                b = (await c.post(items, json={"kind": "note", "note_text": "B"})).json()
                c3 = (await c.post(items, json={"kind": "note", "note_text": "C"})).json()
                c3_hash = c3["current"]["content_hash"]
                # Mover C al inicio (after_item_id = null).
                moved = await c.patch(
                    f"{items}/{c3['evidence_item_id']}/move", json={"after_item_id": None}
                )
                assert moved.status_code == 200, moved.text
                assert _texts((await c.get(items)).json()) == ["C", "A", "B"]
                # Mover B justo después de C (entre C y A).
                await c.patch(
                    f"{items}/{b['evidence_item_id']}/move",
                    json={"after_item_id": c3["evidence_item_id"]},
                )
                listing = (await c.get(items)).json()
                assert _texts(listing) == ["C", "B", "A"]
                # Reordenar NO versiona ni cambia el hash del contenido.
                c3_now = next(i for i in listing if i["evidence_item_id"] == c3["evidence_item_id"])
                assert c3_now["current_version"] == 1
                assert c3_now["current"]["content_hash"] == c3_hash
                # Y los otros tampoco (A sigue en v1).
                assert all(i["current_version"] == 1 for i in listing)
                # 'A' no se vio afectado en contenido.
                assert (
                    next(i for i in listing if i["evidence_item_id"] == a["evidence_item_id"])[
                        "current"
                    ]["content_hash"]
                    == a["current"]["content_hash"]
                )
        finally:
            await cleanup([email])

    run_db_test(scenario, requires="sessions")


def test_exhausting_gaps_triggers_controlled_renumber() -> None:
    async def scenario() -> None:
        email = unique_email("tl-renum")
        try:
            async with client() as c:
                await register_login(c, email)
                sessions = await _owner_project(c)
                sid = (await c.post(sessions, json={"name": "S"})).json()["session_id"]
                items = f"{sessions}/{sid}/items"
                a = (await c.post(items, json={"kind": "note", "note_text": "A"})).json()
                (await c.post(items, json={"kind": "note", "note_text": "Z"})).json()
                # Insertar repetidamente justo después de A agota el hueco (1000→500→…→1) y, al no
                # caber un intermedio, dispara la renumeración controlada. Debe seguir todo en 201.
                for n in range(15):
                    r = await c.post(
                        items,
                        json={
                            "kind": "note",
                            "note_text": f"X{n}",
                            "after_item_id": a["evidence_item_id"],
                        },
                    )
                    assert r.status_code == 201, r.text
                listing = (await c.get(items)).json()
                # 2 + 15 = 17 ítems; posiciones distintas y estrictamente crecientes (orden sano).
                positions = [i["position"] for i in listing]
                assert len(listing) == 17
                assert positions == sorted(positions)
                assert len(set(positions)) == 17
                # A primero, Z al final; los X intercalados justo después de A.
                texts = _texts(listing)
                assert texts[0] == "A"
                assert texts[-1] == "Z"
                assert {t for t in texts if t.startswith("X")} == {f"X{n}" for n in range(15)}
        finally:
            await cleanup([email])

    run_db_test(scenario, requires="sessions")


def test_viewer_cannot_reorder() -> None:
    async def scenario() -> None:
        owner = unique_email("tl-ro-o")
        viewer = unique_email("tl-ro-v")
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
                it = (await co.post(items, json={"kind": "note", "note_text": "A"})).json()
                await co.post(
                    f"/api/v1/workspaces/{wid}/members", json={"email": viewer, "role": "member"}
                )
                await co.post(f"{base}/{pid}/members", json={"email": viewer, "role": "viewer"})
                denied = await cb.patch(
                    f"{items}/{it['evidence_item_id']}/move", json={"after_item_id": None}
                )
                assert denied.status_code == 403, denied.text
        finally:
            await cleanup([owner, viewer])

    run_db_test(scenario, requires="sessions")


def test_move_is_isolated_by_project() -> None:
    async def scenario() -> None:
        email = unique_email("tl-move-iso")
        try:
            async with client() as c:
                await register_login(c, email)
                wid = (await c.post("/api/v1/workspaces", json={"name": "W"})).json()[
                    "workspace_id"
                ]
                base = f"/api/v1/workspaces/{wid}/projects"
                pa = (await c.post(base, json={"name": "A"})).json()["project_id"]
                pb = (await c.post(base, json={"name": "B"})).json()["project_id"]
                sa_url = f"{base}/{pa}/sessions"
                sid = (await c.post(sa_url, json={"name": "S-A"})).json()["session_id"]
                it = (
                    await c.post(f"{sa_url}/{sid}/items", json={"kind": "note", "note_text": "A"})
                ).json()
                # Mover ese ítem por la ruta del proyecto B (ajeno) -> 404.
                cross = f"{base}/{pb}/sessions/{sid}/items/{it['evidence_item_id']}/move"
                assert (await c.patch(cross, json={"after_item_id": None})).status_code == 404
        finally:
            await cleanup([email])

    run_db_test(scenario, requires="sessions")
