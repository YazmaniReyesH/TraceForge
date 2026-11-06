"""Pruebas del análisis de contexto de sesión (F1-T4c): guía efímera de 4 bloques con hash-guard.

NUNCA llaman a la API real: sustituyen el puerto ``AIProvider`` por un doble (``_FakeProvider``) vía
``app.dependency_overrides``. Cubren: los 4 bloques validados + fase; el **hash-guard** (no re-llama
si nada cambió; sí re-llama al reordenar/borrar o con ``force``); que la evidencia se **redacta** y
se envía en **orden de position** (no por fecha); salida inválida → error registrado sin entregar;
``ai_no_evidence``; permisos (viewer lee el último pero no analiza) y aislamiento. Los escenarios
contra la BD usan ``run_db_test(..., requires="ai_session_analyses")`` (omiten si falta la tabla).
"""

from uuid import UUID

import pytest
from cryptography.fernet import Fernet
from httpx import AsyncClient
from sqlalchemy import select

from app.ai.analysis_task import parse_analysis
from app.ai.crypto import RedactionCipher
from app.ai.dependencies import get_ai_provider, get_redaction_cipher
from app.ai.errors import AIInvalidOutputError
from app.ai.port import AICompletion, AIPrompt, AIProvider
from app.core.db import AsyncSessionLocal
from app.main import app
from app.models import SessionAnalysis
from tests._helpers import cleanup, client, register_login, run_db_test, unique_email

_FAKE_ANALYSIS_JSON = (
    '{"siguiente_objetivo": "Enumerar el servicio SSH detectado en 22/tcp.", '
    '"evaluacion": {"estado_actual": "Se detecto 22/tcp abierto (ssh).", '
    '"evidencia_observada": ["22/tcp open ssh"]}, '
    '"validacion_sugerida": [{"comando": "nmap -sC -p22 10.0.0.5", "para_que": "Scripts de SSH"}], '
    '"precauciones": ["No forzar credenciales sin autorizacion"], '
    '"fase_detectada": "enumeración"}'
)

_TEST_KEY = Fernet.generate_key().decode()


# ── Validación de la salida de 4 bloques (unitario, sin BD) ──


def test_parse_valid_four_blocks() -> None:
    payload, model = parse_analysis(_FAKE_ANALYSIS_JSON)
    assert payload["fase_detectada"] == "enumeración"
    assert model.siguiente_objetivo.startswith("Enumerar")
    assert model.evaluacion.estado_actual.startswith("Se detecto")
    assert model.validacion_sugerida[0].comando.startswith("nmap")


def test_parse_strips_code_fence() -> None:
    _, model = parse_analysis("```json\n" + _FAKE_ANALYSIS_JSON + "\n```")
    assert model.fase_detectada.value == "enumeración"


def test_parse_rejects_invalid_shape() -> None:
    with pytest.raises(AIInvalidOutputError):
        parse_analysis('{"siguiente_objetivo": "x"}')  # faltan evaluacion/fase


def test_parse_rejects_unknown_phase() -> None:
    bad = _FAKE_ANALYSIS_JSON.replace('"enumeración"', '"invadir"')
    with pytest.raises(AIInvalidOutputError):
        parse_analysis(bad)


# ── Doble del puerto (para el circuito, sin API real) ──


class _FakeProvider(AIProvider):
    """Doble de ``AIProvider``: cuenta llamadas y guarda el último prompt (redacción/orden)."""

    def __init__(self, *, configured: bool = True, text: str = _FAKE_ANALYSIS_JSON):
        self._configured = configured
        self._text = text
        self.calls = 0
        self.last_prompt: AIPrompt | None = None

    @property
    def name(self) -> str:
        return "fake"

    @property
    def model(self) -> str:
        return "fake-model-2026"

    @property
    def is_configured(self) -> bool:
        return self._configured

    async def complete(self, prompt: AIPrompt, *, max_tokens: int) -> AICompletion:
        self.calls += 1
        self.last_prompt = prompt
        return AICompletion(
            text=self._text, model="fake-model-2026", input_tokens=50, output_tokens=40
        )


def _configured_cipher_override() -> RedactionCipher:
    return RedactionCipher(_TEST_KEY)


def _unconfigured_cipher_override() -> RedactionCipher:
    return RedactionCipher("")


async def _owner_session(c: AsyncClient) -> tuple[str, str]:
    """ws+project+sesión vacía. Devuelve (sbase, sid)."""
    wid = (await c.post("/api/v1/workspaces", json={"name": "W"})).json()["workspace_id"]
    pbase = f"/api/v1/workspaces/{wid}/projects"
    pid = (await c.post(pbase, json={"name": "P"})).json()["project_id"]
    sbase = f"{pbase}/{pid}/sessions"
    sid = (await c.post(sbase, json={"name": "S"})).json()["session_id"]
    return sbase, sid


async def _add_command(c: AsyncClient, sbase: str, sid: str, *, text: str, output: str = "") -> str:
    resp = await c.post(
        f"{sbase}/{sid}/items",
        json={"kind": "command", "command_text": text, "command_output": output},
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["evidence_item_id"])


# ── Circuito del análisis (contra la BD, con doble del puerto) ──


def test_analyze_returns_four_blocks_redacts_and_caches() -> None:
    async def scenario() -> None:
        email = unique_email("an-ok")
        fake = _FakeProvider(configured=True)
        app.dependency_overrides[get_ai_provider] = lambda: fake
        app.dependency_overrides[get_redaction_cipher] = _configured_cipher_override
        try:
            async with client() as c:
                await register_login(c, email)
                sbase, sid = await _owner_session(c)
                await _add_command(
                    c,
                    sbase,
                    sid,
                    text="nmap -sV 10.0.0.5",
                    output="22/tcp open ssh\npassword=Sup3rSecreta!",
                )
                # GET del último antes de analizar => 404 ai_no_analysis.
                pre = await c.get(f"{sbase}/{sid}/analysis")
                assert pre.status_code == 404
                assert pre.json()["code"] == "ai_no_analysis"

                resp = await c.post(f"{sbase}/{sid}/analyze")
                assert resp.status_code == 200, resp.text
                body = resp.json()
                assert body["from_cache"] is False
                assert body["analyzed_item_count"] == 1
                assert body["result"]["fase_detectada"] == "enumeración"
                assert body["result"]["evaluacion"]["estado_actual"]
                assert body["result"]["validacion_sugerida"][0]["comando"].startswith("nmap")
                assert body["provider"] == "fake"
                assert body["prompt_version"] == "session_analysis/v1"
                assert body["ai_call_log_id"] is not None
                assert body["redaction_count"] >= 1
                assert body["redaction_map_stored"] is True
                # La evidencia se redactó ANTES de enviarse y usa prompt caching (bloques).
                assert fake.last_prompt is not None
                assert "Sup3rSecreta" not in fake.last_prompt.user
                assert "[REDACTED_PASSWORD" in fake.last_prompt.user
                assert fake.last_prompt.user_blocks is not None
                assert any(b.cache for b in fake.last_prompt.user_blocks)
                # El mapeo se guardó cifrado (no en claro) y es descifrable.
                async with AsyncSessionLocal() as s:
                    row = (
                        await s.execute(
                            select(SessionAnalysis).where(SessionAnalysis.session_id == UUID(sid))
                        )
                    ).scalar_one()
                    assert row.redaction_ciphertext is not None
                    assert "Sup3rSecreta" not in row.redaction_ciphertext
                    recovered = RedactionCipher(_TEST_KEY).decrypt_mapping(row.redaction_ciphertext)
                    assert "Sup3rSecreta!" in recovered.values()
        finally:
            app.dependency_overrides.pop(get_ai_provider, None)
            app.dependency_overrides.pop(get_redaction_cipher, None)
            await cleanup([email])

    run_db_test(scenario, requires="ai_session_analyses")


def test_hash_guard_skips_second_call() -> None:
    async def scenario() -> None:
        email = unique_email("an-hg")
        fake = _FakeProvider(configured=True)
        app.dependency_overrides[get_ai_provider] = lambda: fake
        app.dependency_overrides[get_redaction_cipher] = _configured_cipher_override
        try:
            async with client() as c:
                await register_login(c, email)
                sbase, sid = await _owner_session(c)
                await _add_command(c, sbase, sid, text="whoami", output="root")
                first = await c.post(f"{sbase}/{sid}/analyze")
                assert first.status_code == 200
                assert first.json()["from_cache"] is False
                assert fake.calls == 1
                # Segundo análisis sin cambios: hash-guard devuelve caché, NO llama al doble.
                second = await c.post(f"{sbase}/{sid}/analyze")
                assert second.status_code == 200
                assert second.json()["from_cache"] is True
                assert fake.calls == 1  # el doble NO se invocó la 2ª vez
        finally:
            app.dependency_overrides.pop(get_ai_provider, None)
            app.dependency_overrides.pop(get_redaction_cipher, None)
            await cleanup([email])

    run_db_test(scenario, requires="ai_session_analyses")


def test_force_recalls_even_if_hash_matches() -> None:
    async def scenario() -> None:
        email = unique_email("an-force")
        fake = _FakeProvider(configured=True)
        app.dependency_overrides[get_ai_provider] = lambda: fake
        app.dependency_overrides[get_redaction_cipher] = _configured_cipher_override
        try:
            async with client() as c:
                await register_login(c, email)
                sbase, sid = await _owner_session(c)
                await _add_command(c, sbase, sid, text="id", output="uid=0")
                assert (await c.post(f"{sbase}/{sid}/analyze")).json()["from_cache"] is False
                assert fake.calls == 1
                forced = await c.post(f"{sbase}/{sid}/analyze?force=true")
                assert forced.status_code == 200
                assert forced.json()["from_cache"] is False
                assert fake.calls == 2  # force vuelve a llamar aunque el hash coincida
        finally:
            app.dependency_overrides.pop(get_ai_provider, None)
            app.dependency_overrides.pop(get_redaction_cipher, None)
            await cleanup([email])

    run_db_test(scenario, requires="ai_session_analyses")


def test_reorder_changes_hash_and_sends_position_order() -> None:
    async def scenario() -> None:
        email = unique_email("an-order")
        fake = _FakeProvider(configured=True)
        app.dependency_overrides[get_ai_provider] = lambda: fake
        app.dependency_overrides[get_redaction_cipher] = _configured_cipher_override
        try:
            async with client() as c:
                await register_login(c, email)
                sbase, sid = await _owner_session(c)
                _id_a = await _add_command(c, sbase, sid, text="echo alpha")
                id_b = await _add_command(c, sbase, sid, text="echo bravo")
                await c.post(f"{sbase}/{sid}/analyze")
                assert fake.calls == 1
                assert fake.last_prompt is not None
                # Orden inicial por position: alpha antes que bravo.
                assert fake.last_prompt.user.index("alpha") < fake.last_prompt.user.index("bravo")
                # Mover bravo al inicio (position menor, pero created_at MAYOR que alpha).
                moved = await c.patch(
                    f"{sbase}/{sid}/items/{id_b}/move", json={"after_item_id": None}
                )
                assert moved.status_code == 200, moved.text
                second = await c.post(f"{sbase}/{sid}/analyze")
                assert second.status_code == 200
                # Reordenar cambió el hash => re-llama (no from_cache).
                assert second.json()["from_cache"] is False
                assert fake.calls == 2
                # Ahora se envía en ORDEN DE POSITION (bravo antes que alpha), no por fecha.
                assert fake.last_prompt.user.index("bravo") < fake.last_prompt.user.index("alpha")
        finally:
            app.dependency_overrides.pop(get_ai_provider, None)
            app.dependency_overrides.pop(get_redaction_cipher, None)
            await cleanup([email])

    run_db_test(scenario, requires="ai_session_analyses")


def test_delete_item_changes_hash_and_recalls() -> None:
    async def scenario() -> None:
        email = unique_email("an-del")
        fake = _FakeProvider(configured=True)
        app.dependency_overrides[get_ai_provider] = lambda: fake
        app.dependency_overrides[get_redaction_cipher] = _configured_cipher_override
        try:
            async with client() as c:
                await register_login(c, email)
                sbase, sid = await _owner_session(c)
                await _add_command(c, sbase, sid, text="echo uno")
                id_b = await _add_command(c, sbase, sid, text="echo dos")
                assert (await c.post(f"{sbase}/{sid}/analyze")).json()["analyzed_item_count"] == 2
                assert fake.calls == 1
                assert (await c.delete(f"{sbase}/{sid}/items/{id_b}")).status_code == 204
                again = await c.post(f"{sbase}/{sid}/analyze")
                assert again.status_code == 200
                assert again.json()["from_cache"] is False  # borrar cambió el hash
                assert again.json()["analyzed_item_count"] == 1
                assert fake.calls == 2
        finally:
            app.dependency_overrides.pop(get_ai_provider, None)
            app.dependency_overrides.pop(get_redaction_cipher, None)
            await cleanup([email])

    run_db_test(scenario, requires="ai_session_analyses")


def test_invalid_output_rejected_and_logged_not_delivered() -> None:
    async def scenario() -> None:
        email = unique_email("an-bad")
        fake = _FakeProvider(configured=True, text="esto no es json")
        app.dependency_overrides[get_ai_provider] = lambda: fake
        app.dependency_overrides[get_redaction_cipher] = _configured_cipher_override
        try:
            async with client() as c:
                await register_login(c, email)
                sbase, sid = await _owner_session(c)
                await _add_command(c, sbase, sid, text="ls")
                resp = await c.post(f"{sbase}/{sid}/analyze")
                assert resp.status_code == 502, resp.text
                assert resp.json()["code"] == "ai_invalid_output"
                # No se entrega ni se cachea una guía inválida.
                async with AsyncSessionLocal() as s:
                    rows = (
                        (
                            await s.execute(
                                select(SessionAnalysis).where(
                                    SessionAnalysis.session_id == UUID(sid)
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )
                    assert rows == []
        finally:
            app.dependency_overrides.pop(get_ai_provider, None)
            app.dependency_overrides.pop(get_redaction_cipher, None)
            await cleanup([email])

    run_db_test(scenario, requires="ai_session_analyses")


def test_no_evidence_rejected() -> None:
    async def scenario() -> None:
        email = unique_email("an-noev")
        fake = _FakeProvider(configured=True)
        app.dependency_overrides[get_ai_provider] = lambda: fake
        try:
            async with client() as c:
                await register_login(c, email)
                sbase, sid = await _owner_session(c)  # sin ítems
                resp = await c.post(f"{sbase}/{sid}/analyze")
                assert resp.status_code == 409, resp.text
                assert resp.json()["code"] == "ai_no_evidence"
                assert fake.calls == 0
        finally:
            app.dependency_overrides.pop(get_ai_provider, None)
            await cleanup([email])

    run_db_test(scenario, requires="ai_session_analyses")


def test_not_configured_degrades() -> None:
    async def scenario() -> None:
        email = unique_email("an-nc")
        fake = _FakeProvider(configured=False)
        app.dependency_overrides[get_ai_provider] = lambda: fake
        try:
            async with client() as c:
                await register_login(c, email)
                sbase, sid = await _owner_session(c)
                await _add_command(c, sbase, sid, text="ls")
                resp = await c.post(f"{sbase}/{sid}/analyze")
                assert resp.status_code == 503, resp.text
                assert resp.json()["code"] == "ai_not_configured"
                assert fake.calls == 0
        finally:
            app.dependency_overrides.pop(get_ai_provider, None)
            await cleanup([email])

    run_db_test(scenario, requires="ai_session_analyses")


def test_without_encryption_key_degrades_safely() -> None:
    async def scenario() -> None:
        email = unique_email("an-nokey")
        fake = _FakeProvider(configured=True)
        app.dependency_overrides[get_ai_provider] = lambda: fake
        # Cifrador SIN clave forzado (independiente del TF_ENCRYPTION_KEY del entorno).
        app.dependency_overrides[get_redaction_cipher] = _unconfigured_cipher_override
        try:
            async with client() as c:
                await register_login(c, email)
                sbase, sid = await _owner_session(c)
                await _add_command(
                    c, sbase, sid, text="cat id_rsa", output="password=Sup3rSecreta!"
                )
                resp = await c.post(f"{sbase}/{sid}/analyze")
                assert resp.status_code == 200, resp.text
                body = resp.json()
                assert body["redaction_count"] >= 1
                assert body["redaction_map_stored"] is False  # no se guardó (nunca en claro)
                async with AsyncSessionLocal() as s:
                    row = (
                        await s.execute(
                            select(SessionAnalysis).where(SessionAnalysis.session_id == UUID(sid))
                        )
                    ).scalar_one()
                    assert row.redaction_ciphertext is None
        finally:
            app.dependency_overrides.pop(get_ai_provider, None)
            app.dependency_overrides.pop(get_redaction_cipher, None)
            await cleanup([email])

    run_db_test(scenario, requires="ai_session_analyses")


def test_viewer_can_read_last_but_not_analyze() -> None:
    async def scenario() -> None:
        owner = unique_email("an-v-o")
        viewer = unique_email("an-v-b")
        fake = _FakeProvider(configured=True)
        app.dependency_overrides[get_ai_provider] = lambda: fake
        app.dependency_overrides[get_redaction_cipher] = _configured_cipher_override
        try:
            async with client() as co, client() as cb:
                await register_login(co, owner)
                await register_login(cb, viewer)
                sbase, sid = await _owner_session(co)
                await _add_command(co, sbase, sid, text="whoami", output="root")
                await co.post(f"{sbase}/{sid}/analyze")  # owner crea el análisis
                parts = sbase.split("/")
                wid, pid = parts[4], parts[6]
                await co.post(
                    f"/api/v1/workspaces/{wid}/members", json={"email": viewer, "role": "member"}
                )
                await co.post(
                    f"/api/v1/workspaces/{wid}/projects/{pid}/members",
                    json={"email": viewer, "role": "viewer"},
                )
                calls_before = fake.calls
                # Viewer PUEDE leer el último análisis...
                got = await cb.get(f"{sbase}/{sid}/analysis")
                assert got.status_code == 200, got.text
                assert got.json()["from_cache"] is True
                # ...pero NO puede analizar (403) y no dispara ninguna llamada.
                denied = await cb.post(f"{sbase}/{sid}/analyze")
                assert denied.status_code == 403, denied.text
                assert fake.calls == calls_before
        finally:
            app.dependency_overrides.pop(get_ai_provider, None)
            app.dependency_overrides.pop(get_redaction_cipher, None)
            await cleanup([owner, viewer])

    run_db_test(scenario, requires="ai_session_analyses")


def test_analysis_isolated_from_non_members() -> None:
    async def scenario() -> None:
        owner = unique_email("an-iso-o")
        outsider = unique_email("an-iso-x")
        fake = _FakeProvider(configured=True)
        app.dependency_overrides[get_ai_provider] = lambda: fake
        try:
            async with client() as co, client() as cx:
                await register_login(co, owner)
                await register_login(cx, outsider)
                sbase, sid = await _owner_session(co)
                await _add_command(co, sbase, sid, text="ls")
                # Quien no es miembro no ve el project -> 404 (no se revela su existencia).
                assert (await cx.post(f"{sbase}/{sid}/analyze")).status_code == 404
                assert (await cx.get(f"{sbase}/{sid}/analysis")).status_code == 404
                assert fake.calls == 0
        finally:
            app.dependency_overrides.pop(get_ai_provider, None)
            await cleanup([owner, outsider])

    run_db_test(scenario, requires="ai_session_analyses")
