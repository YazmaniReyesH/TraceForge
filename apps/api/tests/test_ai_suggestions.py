"""Pruebas de la función de IA de producto (F1-T4a): sugerencias con procedencia y cifrado.

Las pruebas **nunca** llaman a la API real: sustituyen el puerto ``AIProvider`` por un doble
(``_FakeProvider``) vía ``app.dependency_overrides``. Cubren: cifrado round-trip del mapeo;
validación de la salida estructurada (ADR-0004); el circuito generar (redactar→cifrar→ensamblar→
llamar→validar→persistir) creando una sugerencia ``pending`` con procedencia, con la evidencia
redactada ANTES de "enviarse" y el mapeo persistido **cifrado** (y no en claro); el comportamiento
seguro sin ``TF_ENCRYPTION_KEY``; aceptar/editar (transiciones + conservación del original);
"IA no configurada" degrada; permisos (viewer 403) y aislamiento (404). Los escenarios contra la BD
usan ``run_db_test(..., requires="ai_suggestions")`` (omiten si falta la migración).
"""

from uuid import UUID

from cryptography.fernet import Fernet
from httpx import AsyncClient
from sqlalchemy import select

from app.ai.crypto import RedactionCipher
from app.ai.dependencies import get_ai_provider, get_redaction_cipher
from app.ai.errors import AIInvalidOutputError
from app.ai.port import AICompletion, AIPrompt, AIProvider
from app.ai.tasks import TASKS, DescriptionOutput, NextStepOutput
from app.core.db import AsyncSessionLocal
from app.main import app
from app.models import AIRedactionMap, AISuggestion
from app.models.enums import AISuggestionKind
from tests._helpers import cleanup, client, register_login, run_db_test, unique_email

# Salida del doble: JSON con las claves de AMBAS tareas (los modelos ignoran claves extra), así un
# mismo doble sirve para description y next_step.
_FAKE_JSON = (
    '{"description": "Se ejecuto un escaneo nmap que hallo el puerto 22/tcp abierto (ssh).", '
    '"next_step": "Enumerar el servicio SSH con los scripts de nmap.", '
    '"rationale": "El puerto 22/tcp aparece abierto en la evidencia."}'
)


# ── Cifrado del mapeo (unitario, sin BD) ──


def test_cipher_roundtrip_and_never_plaintext() -> None:
    cipher = RedactionCipher(Fernet.generate_key().decode())
    assert cipher.is_configured
    mapping = {"[REDACTED_PASSWORD_1]": "Sup3rSecreta!", "[REDACTED_API_KEY_1]": "sk-ant-deadbeef"}
    token = cipher.encrypt_mapping(mapping)
    assert "Sup3rSecreta!" not in token  # jamas en claro
    assert "sk-ant-deadbeef" not in token
    assert cipher.decrypt_mapping(token) == mapping  # rehidratacion


def test_cipher_without_key_is_not_configured() -> None:
    assert RedactionCipher("").is_configured is False
    assert RedactionCipher("clave-invalida-no-fernet").is_configured is False


# ── Validación de salida estructurada (unitario, sin BD) ──


def test_task_parse_valid_output() -> None:
    payload, content = TASKS[AISuggestionKind.DESCRIPTION].parse(_FAKE_JSON)
    assert content.startswith("Se ejecuto")
    assert payload == {
        "description": "Se ejecuto un escaneo nmap que hallo el puerto 22/tcp abierto (ssh)."
    }
    _, next_content = TASKS[AISuggestionKind.NEXT_STEP].parse(_FAKE_JSON)
    assert next_content.startswith("Enumerar")


def test_task_parse_strips_code_fence() -> None:
    fenced = "```json\n" + _FAKE_JSON + "\n```"
    _, content = TASKS[AISuggestionKind.DESCRIPTION].parse(fenced)
    assert content.startswith("Se ejecuto")


def test_task_parse_rejects_invalid_shape() -> None:
    task = TASKS[AISuggestionKind.DESCRIPTION]
    for bad in ("no soy json", "{}", '{"otra": "cosa"}', '{"description": ""}'):
        try:
            task.parse(bad)
        except AIInvalidOutputError:
            continue
        raise AssertionError(f"debio rechazar: {bad!r}")


def test_output_models_require_fields() -> None:
    assert DescriptionOutput(description="x").content == "x"
    assert NextStepOutput(next_step="n", rationale="r").content == "n"


# ── Doble del puerto (para el circuito, sin API real) ──


class _FakeProvider(AIProvider):
    """Doble de ``AIProvider``: ni red ni coste. Guarda el último prompt (para ver la redacción)."""

    def __init__(self, *, configured: bool = True, text: str = _FAKE_JSON, raises: bool = False):
        self._configured = configured
        self._text = text
        self._raises = raises
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
        if self._raises:
            from app.ai.errors import AIProviderError

            raise AIProviderError()
        return AICompletion(
            text=self._text,
            model="fake-model-2026",
            input_tokens=20,
            output_tokens=9,
            stop_reason="end_turn",
        )


async def _owner_session_with_evidence(c: AsyncClient) -> tuple[str, str]:
    """Crea ws+project+sesión con un ítem de evidencia (con secreto). Devuelve (base, sid)."""
    wid = (await c.post("/api/v1/workspaces", json={"name": "W"})).json()["workspace_id"]
    pbase = f"/api/v1/workspaces/{wid}/projects"
    pid = (await c.post(pbase, json={"name": "P"})).json()["project_id"]
    sbase = f"{pbase}/{pid}/sessions"
    sid = (await c.post(sbase, json={"name": "S"})).json()["session_id"]
    await c.post(
        f"{sbase}/{sid}/items",
        json={
            "kind": "command",
            "command_text": "nmap -sV 10.0.0.5",
            "command_output": "22/tcp open ssh\npassword=Sup3rSecreta!",
        },
    )
    return sbase, sid


def _configured_cipher_override() -> RedactionCipher:
    return RedactionCipher(_TEST_KEY)


def _unconfigured_cipher_override() -> RedactionCipher:
    """Cifrador SIN clave, independiente del ``TF_ENCRYPTION_KEY`` del entorno de ejecución."""
    return RedactionCipher("")


_TEST_KEY = Fernet.generate_key().decode()


# ── Circuito de generación (contra la BD, con doble del puerto) ──


def test_generate_creates_pending_with_provenance_and_encrypted_map() -> None:
    async def scenario() -> None:
        email = unique_email("sug-ok")
        fake = _FakeProvider(configured=True)
        app.dependency_overrides[get_ai_provider] = lambda: fake
        app.dependency_overrides[get_redaction_cipher] = _configured_cipher_override
        try:
            async with client() as c:
                await register_login(c, email)
                sbase, sid = await _owner_session_with_evidence(c)
                resp = await c.post(f"{sbase}/{sid}/suggestions", json={"kind": "description"})
                assert resp.status_code == 201, resp.text
                body = resp.json()
                # Nace pending con procedencia completa (ADR-0003).
                assert body["status"] == "pending"
                assert body["kind"] == "description"
                assert body["suggested_content"].startswith("Se ejecuto")
                assert body["edited_content"] is None
                assert body["provider"] == "fake"
                assert body["model"] == "fake-model-2026"
                assert body["prompt_version"] == "description/v1"
                assert body["ai_call_log_id"] is not None
                assert body["input_refs"]["session_id"] == sid
                assert len(body["input_refs"]["evidence"]) == 1
                assert body["redaction_count"] >= 1
                assert body["redaction_map_stored"] is True
                # La evidencia se redactó ANTES de "enviarse" al proveedor (doble).
                assert fake.last_prompt is not None
                assert "Sup3rSecreta" not in fake.last_prompt.user
                assert "[REDACTED_" in fake.last_prompt.user
                assert "<<EVIDENCIA_" in fake.last_prompt.user  # anti-inyección
                # El mapeo se guardó CIFRADO (y no en claro); se puede rehidratar.
                async with AsyncSessionLocal() as s:
                    rmap = (
                        await s.execute(
                            select(AIRedactionMap).where(
                                AIRedactionMap.ai_suggestion_id == UUID(body["ai_suggestion_id"])
                            )
                        )
                    ).scalar_one()
                    assert "Sup3rSecreta" not in rmap.ciphertext
                    assert rmap.scheme == "fernet"
                    recovered = RedactionCipher(_TEST_KEY).decrypt_mapping(rmap.ciphertext)
                    assert "Sup3rSecreta!" in recovered.values()
        finally:
            app.dependency_overrides.pop(get_ai_provider, None)
            app.dependency_overrides.pop(get_redaction_cipher, None)
            await cleanup([email])

    run_db_test(scenario, requires="ai_suggestions")


def test_generate_without_encryption_key_degrades_safely() -> None:
    async def scenario() -> None:
        email = unique_email("sug-nokey")
        fake = _FakeProvider(configured=True)
        app.dependency_overrides[get_ai_provider] = lambda: fake
        # Se fuerza un cifrador SIN clave (no depende del TF_ENCRYPTION_KEY del entorno): así la
        # prueba es determinista aunque el equipo haya configurado la clave en su .env.
        app.dependency_overrides[get_redaction_cipher] = _unconfigured_cipher_override
        try:
            async with client() as c:
                await register_login(c, email)
                sbase, sid = await _owner_session_with_evidence(c)
                resp = await c.post(f"{sbase}/{sid}/suggestions", json={"kind": "description"})
                assert resp.status_code == 201, resp.text
                body = resp.json()
                # La sugerencia se crea igual, pero el mapeo NO se persiste (nunca en claro).
                assert body["redaction_count"] >= 1
                assert body["redaction_map_stored"] is False
                async with AsyncSessionLocal() as s:
                    rows = (
                        (
                            await s.execute(
                                select(AIRedactionMap).where(
                                    AIRedactionMap.ai_suggestion_id
                                    == UUID(body["ai_suggestion_id"])
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )
                    assert rows == []  # no se guardó mapeo
        finally:
            app.dependency_overrides.pop(get_ai_provider, None)
            app.dependency_overrides.pop(get_redaction_cipher, None)
            await cleanup([email])

    run_db_test(scenario, requires="ai_suggestions")


def test_generate_next_step_kind() -> None:
    async def scenario() -> None:
        email = unique_email("sug-ns")
        fake = _FakeProvider(configured=True)
        app.dependency_overrides[get_ai_provider] = lambda: fake
        try:
            async with client() as c:
                await register_login(c, email)
                sbase, sid = await _owner_session_with_evidence(c)
                resp = await c.post(f"{sbase}/{sid}/suggestions", json={"kind": "next_step"})
                assert resp.status_code == 201, resp.text
                body = resp.json()
                assert body["kind"] == "next_step"
                assert body["suggested_content"].startswith("Enumerar")
                assert body["suggested_payload"]["rationale"].startswith("El puerto")
        finally:
            app.dependency_overrides.pop(get_ai_provider, None)
            await cleanup([email])

    run_db_test(scenario, requires="ai_suggestions")


def test_generate_not_configured_degrades() -> None:
    async def scenario() -> None:
        email = unique_email("sug-nc")
        fake = _FakeProvider(configured=False)
        app.dependency_overrides[get_ai_provider] = lambda: fake
        try:
            async with client() as c:
                await register_login(c, email)
                sbase, sid = await _owner_session_with_evidence(c)
                resp = await c.post(f"{sbase}/{sid}/suggestions", json={"kind": "description"})
                assert resp.status_code == 503, resp.text
                assert resp.json()["code"] == "ai_not_configured"
                assert fake.calls == 0
                async with AsyncSessionLocal() as s:
                    rows = (await s.execute(select(AISuggestion))).scalars().all()
                    assert all(str(r.created_by) for r in rows)  # ninguna sugerencia creada aquí
                    mine = [r for r in rows if r.session_id == UUID(sid)]
                    assert mine == []
        finally:
            app.dependency_overrides.pop(get_ai_provider, None)
            await cleanup([email])

    run_db_test(scenario, requires="ai_suggestions")


def test_generate_invalid_output_rejected() -> None:
    async def scenario() -> None:
        email = unique_email("sug-bad")
        fake = _FakeProvider(configured=True, text="esto no es json")
        app.dependency_overrides[get_ai_provider] = lambda: fake
        try:
            async with client() as c:
                await register_login(c, email)
                sbase, sid = await _owner_session_with_evidence(c)
                resp = await c.post(f"{sbase}/{sid}/suggestions", json={"kind": "description"})
                assert resp.status_code == 502, resp.text
                assert resp.json()["code"] == "ai_invalid_output"
                async with AsyncSessionLocal() as s:
                    mine = [
                        r
                        for r in (await s.execute(select(AISuggestion))).scalars().all()
                        if r.session_id == UUID(sid)
                    ]
                    assert mine == []  # no se persiste forma inválida
        finally:
            app.dependency_overrides.pop(get_ai_provider, None)
            await cleanup([email])

    run_db_test(scenario, requires="ai_suggestions")


def test_generate_no_evidence_rejected() -> None:
    async def scenario() -> None:
        email = unique_email("sug-noev")
        fake = _FakeProvider(configured=True)
        app.dependency_overrides[get_ai_provider] = lambda: fake
        try:
            async with client() as c:
                await register_login(c, email)
                wid = (await c.post("/api/v1/workspaces", json={"name": "W"})).json()[
                    "workspace_id"
                ]
                pbase = f"/api/v1/workspaces/{wid}/projects"
                pid = (await c.post(pbase, json={"name": "P"})).json()["project_id"]
                sbase = f"{pbase}/{pid}/sessions"
                sid = (await c.post(sbase, json={"name": "S"})).json()["session_id"]
                resp = await c.post(f"{sbase}/{sid}/suggestions", json={"kind": "description"})
                assert resp.status_code == 409, resp.text
                assert resp.json()["code"] == "ai_no_evidence"
                assert fake.calls == 0
        finally:
            app.dependency_overrides.pop(get_ai_provider, None)
            await cleanup([email])

    run_db_test(scenario, requires="ai_suggestions")


def test_accept_and_edit_transitions_preserve_original() -> None:
    async def scenario() -> None:
        email = unique_email("sug-tr")
        fake = _FakeProvider(configured=True)
        app.dependency_overrides[get_ai_provider] = lambda: fake
        try:
            async with client() as c:
                uid = await register_login(c, email)
                sbase, sid = await _owner_session_with_evidence(c)
                base = f"{sbase}/{sid}/suggestions"

                # Aceptar: pending -> accepted (con auditoría) y re-aceptar falla (terminal).
                sug = (await c.post(base, json={"kind": "description"})).json()
                sidd = sug["ai_suggestion_id"]
                acc = await c.post(f"{base}/{sidd}/accept")
                assert acc.status_code == 200, acc.text
                assert acc.json()["status"] == "accepted"
                assert acc.json()["reviewed_by"] == str(uid)
                assert acc.json()["reviewed_at"] is not None
                assert (await c.post(f"{base}/{sidd}/accept")).status_code == 409
                # No se puede editar una aceptada (terminal).
                assert (
                    await c.post(f"{base}/{sidd}/edit", json={"content": "x"})
                ).status_code == 409

                # Editar: pending -> edited; conserva el original; admite re-edición.
                sug2 = (await c.post(base, json={"kind": "description"})).json()
                sid2 = sug2["ai_suggestion_id"]
                original = sug2["suggested_content"]
                ed = await c.post(f"{base}/{sid2}/edit", json={"content": "Texto humano corregido"})
                assert ed.status_code == 200, ed.text
                assert ed.json()["status"] == "edited"
                assert ed.json()["edited_content"] == "Texto humano corregido"
                assert ed.json()["suggested_content"] == original  # original intacto
                assert ed.json()["provider"] == "fake"  # rastro de origen IA conservado
                ed2 = await c.post(f"{base}/{sid2}/edit", json={"content": "Otra correccion"})
                assert ed2.status_code == 200  # edited -> edited permitido
                assert ed2.json()["edited_content"] == "Otra correccion"
        finally:
            app.dependency_overrides.pop(get_ai_provider, None)
            await cleanup([email])

    run_db_test(scenario, requires="ai_suggestions")


def test_viewer_cannot_generate_but_can_list() -> None:
    async def scenario() -> None:
        owner = unique_email("sug-v-o")
        viewer = unique_email("sug-v-b")
        fake = _FakeProvider(configured=True)
        app.dependency_overrides[get_ai_provider] = lambda: fake
        try:
            async with client() as co, client() as cb:
                await register_login(co, owner)
                await register_login(cb, viewer)
                sbase, sid = await _owner_session_with_evidence(co)
                # wid/pid de la ruta para dar de alta al viewer.
                parts = sbase.split("/")
                wid, pid = parts[4], parts[6]
                await co.post(
                    f"/api/v1/workspaces/{wid}/members", json={"email": viewer, "role": "member"}
                )
                await co.post(
                    f"/api/v1/workspaces/{wid}/projects/{pid}/members",
                    json={"email": viewer, "role": "viewer"},
                )
                base = f"{sbase}/{sid}/suggestions"
                assert (await cb.get(base)).status_code == 200  # puede listar
                denied = await cb.post(base, json={"kind": "description"})
                assert denied.status_code == 403, denied.text
                assert fake.calls == 0
        finally:
            app.dependency_overrides.pop(get_ai_provider, None)
            await cleanup([owner, viewer])

    run_db_test(scenario, requires="ai_suggestions")


def test_suggestions_isolated_from_non_members() -> None:
    async def scenario() -> None:
        owner = unique_email("sug-iso-o")
        outsider = unique_email("sug-iso-x")
        fake = _FakeProvider(configured=True)
        app.dependency_overrides[get_ai_provider] = lambda: fake
        try:
            async with client() as co, client() as cx:
                await register_login(co, owner)
                await register_login(cx, outsider)
                sbase, sid = await _owner_session_with_evidence(co)
                base = f"{sbase}/{sid}/suggestions"
                # Quien no es miembro no ve el project -> 404 (no se revela su existencia).
                assert (await cx.post(base, json={"kind": "description"})).status_code == 404
                assert (await cx.get(base)).status_code == 404
                assert fake.calls == 0
        finally:
            app.dependency_overrides.pop(get_ai_provider, None)
            await cleanup([owner, outsider])

    run_db_test(scenario, requires="ai_suggestions")
