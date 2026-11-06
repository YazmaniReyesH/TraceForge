# Ficha de módulo: ia (gateway de IA)

- **Fase / tanda:** F1-T3 (andamiaje) · **F1-T4a** (1ª función de producto: sugerencias, solo backend)
- **Estado del módulo:** gateway `AIProvider` con Claude detrás del puerto; **redacción** determinista
  de secretos; **ensamblado** anti-inyección; **bitácora** (`ai_call_log`); **ping verificable**; y
  **sugerencias de IA** (`description` / `next_step`) a partir de la evidencia **real** de una sesión,
  con **procedencia** (ADR-0003), **salida estructurada validada** (ADR-0004) y **mapeo de redacción
  cifrado** (ADR-0016), más su máquina de estados (pending→accepted/edited). **Sin UI ni el violeta de
  IA** (F1-T4b), sin rehidratación efectiva, sin otros proveedores.
- **Última actualización:** 2026-11-06

## Propósito

Dar los cimientos para usar **IA en la nube** como motor de asistencia respetando los principios
fundacionales: la IA **propone** y el código **valida** (ADR-0004), todo contenido de IA es una
**sugerencia con procedencia** (ADR-0003), y **nada cruza el perímetro sin redacción** y auditoría
(ADR-0005). Esta tanda no implementa ninguna función de producto: prepara el puerto, la redacción, el
ensamblado anti-inyección y la bitácora, y los verifica con un ping real a Claude.

## Capas y archivos

```
app/ai/
  port.py             # Puerto AIProvider (dominio): AIPrompt, AICompletion, complete()/name/model/is_configured
  claude_provider.py  # Implementación Claude (SDK anthropic, import perezoso); model override (ai_policy)
  errors.py           # AIError + AINotConfigured(503)/AIProvider(502)/AIInvalidOutput(502)/AINoEvidence(409)/…
  redaction.py        # redact(text) -> RedactionResult (texto redactado + mapa en memoria + conteo)
  prompt.py           # assemble_prompt(instruction, evidence): evidencia delimitada como dato no confiable
  crypto.py           # RedactionCipher (Fernet): cifra/descifra el mapeo marcador→valor (ADR-0016)
  tasks.py            # Registro de AI tasks (description/next_step): prompt versionado + salida validada
  schemas.py          # AIStatusRead, AIPingResult, AISuggestion{Generate,Edit,Read}
  repository.py       # AICallLogRepository (acotado a workspace+project) — solo inserta
  suggestions_repository.py  # AISuggestionRepository (sugerencias + mapeo cifrado) — aislado
  service.py          # AIService: redactar → ensamblar → proveedor → bitácora (+ ping sintético)
  suggestions_service.py     # AISuggestionService: generar/aceptar/editar (circuito F1-T4a)
  dependencies.py     # get_ai_provider (lee ai_policy), get_redaction_cipher, get_ai_(suggestion_)service
  router.py           # /…/ai  (GET /status, POST /ping)
  suggestions_router.py      # /…/sessions/{sid}/suggestions (POST, GET, {id}/accept, {id}/edit)
app/models/
  ai_call_log.py      # AICallLog (tabla ai_call_log)
  ai_suggestion.py    # AISuggestion (tabla ai_suggestions): contenido + procedencia + estado
  ai_redaction_map.py # AIRedactionMap (tabla ai_redaction_maps): mapeo marcador→valor CIFRADO
```

Respeta las capas `router → service → repository`. El servicio **arma el prompt** (redacción +
ensamblado) y llama al **puerto**; el puerto solo habla con el SDK y **normaliza** la respuesta a
tipos del dominio. El `AICallLogRepository` se construye con `workspace_id`/`project_id` del
**contexto de proyecto** (gate ya aplicado en el router), nunca del cliente → **aislamiento** por
defecto. La identidad (`created_by`) sale del token.

## Puerto `AIProvider` (port/adapter)

Interfaz de **dominio** (no del SDK), como `AuthProvider` (ADR-0007) y el storage:

- `name: str` (p. ej. `"claude"`), `model: str` (de settings), `is_configured: bool`.
- `async complete(prompt: AIPrompt, *, max_tokens: int) -> AICompletion`.
- `AIPrompt{system, user}` y `AICompletion{text, model, input_tokens, output_tokens, stop_reason}`.

**Claude** (`claude_provider.py`) va detrás: importa `anthropic` de forma **perezosa** (la app
arranca aunque no esté instalado), maneja ausencia de API key (`is_configured=False`), y traduce
errores de red/API/timeout a `AIProviderError` **sin filtrar secretos** (mensaje genérico; solo el
`code` llega a la bitácora). **Dónde encajan OpenAI/Gemini (F4):** otra implementación de
`AIProvider` seleccionada en `get_ai_provider` (p. ej. según settings o política del proyecto); el
servicio y los endpoints no cambian.

- **Modelo por defecto:** `claude-sonnet-4-5`, configurable por `TF_ANTHROPIC_MODEL` (no se clava en
  código). `TF_ANTHROPIC_MAX_TOKENS` y `TF_ANTHROPIC_TIMEOUT_SECONDS` también configurables.
- **API key:** `TF_ANTHROPIC_API_KEY`. Vacía ⇒ estado "IA no configurada" (degrada, no rompe). Nunca
  en el repo ni en logs/bitácora.

## Redacción de secretos (determinista, NO IA)

`redact(text) -> RedactionResult(text, mapping, count)`. Marcadores **estables**
(`[REDACTED_<TIPO>_<n>]`): el mismo secreto produce el mismo marcador dentro de un texto. El mapa
marcador→valor queda **en memoria** (en F1-T3 **no se persiste**; el mapeo cifrado es F1-T4).

| Tipo (marcador) | Qué cubre (resumen) |
|---|---|
| `PRIVATE_KEY` | Bloque PEM `BEGIN … PRIVATE KEY … END` (completo) |
| `JWT` | Token JWT (`eyJ…`.`…`.`…`) |
| `AWS_KEY` | AWS Access Key ID (`AKIA…`) |
| `API_KEY` | Claves `sk-`/`pk-`/`rk-` (OpenAI/Anthropic/Stripe) |
| `TOKEN` | Token tras `Bearer ` (conserva "Bearer ") |
| `SECRET` | Valor de `api_key/secret/token/access_key/auth_token = …` |
| `PASSWORD` | Valor de `password/passwd/pwd = …` |
| `HASH` | Hash hex: sha256 (64) / sha1 (40) / md5 (32) |

**Qué NO se redacta (por ahora):** PII e IPs (dependen de la política/clasificación del proyecto, aún
reservada en `projects.ai_policy`). Tampoco texto que no case ningún patrón.

**Equilibrio (ADR-0015):** preserva la **estructura** que el modelo necesita entender — en una
asignación enmascara solo el valor y conserva la clave (`password=[REDACTED_PASSWORD_1]`). Redactar de
más rompería lo que el modelo debe analizar.

**Relación con el realce semántico (F1-T2):** comparten la *forma* del patrón de hash pero **no se
acoplan** (oculta vs colorea; Python vs TypeScript; metas opuestas). Decisión en ADR-0015.

`[[POR LLENAR: la redacción determinista nunca es perfecta ante datos arbitrarios; el catálogo de
patrones debe revisarse/ampliarse y la redacción de PII/IPs por clasificación se definirá en F1-T4.]]`

## Ensamblado anti-inyección

`assemble_prompt(instruction, evidence) -> AIPrompt`. La evidencia (ya redactada) de un objetivo de
pentest es **contenido no confiable**: puede traer inyección de prompt. El ensamblado la envuelve en
una **frontera única con nonce** por llamada (`<<EVIDENCIA_xxxx>> … <<FIN_EVIDENCIA_xxxx>>`) y el
`system` instruye al modelo a tratar todo lo de dentro como **datos**, nunca instrucciones. La tarea
(confiable) va **fuera** de la frontera. El nonce impide que la evidencia "cierre" o suplante la
frontera.

## Bitácora de llamadas (`ai_call_log`)

Una fila por llamada (append-only en la práctica). **Qué guarda y por qué:** ADR-0015. Columnas:
`ai_call_log_id` (PK), `workspace_id`/`project_id` (FK CASCADE, indexados; aislamiento), `provider`,
`model`, `status` (`ok|error|not_configured`, CHECK `ck_ai_call_log_status`), `input_tokens`/
`output_tokens`, `redacted_prompt` (lo enviado **ya redactado**), `redacted_prompt_sha256`,
`redaction_count`, `error_code` (código estable, sin secretos), `created_by` (FK RESTRICT),
`created_at`. **Nunca** guarda el contenido crudo, el mapeo marcador→valor, ni la API key.

## Función de producto: sugerencias de IA (F1-T4a)

Primera función de IA de cara al producto: a partir de la evidencia **real** de una sesión, genera una
sugerencia (`description` o `next_step`) que **nace `pending`** y que el usuario **acepta** o **edita**.

**Flujo del servicio** (`AISuggestionService.generate`, respeta router→service→repository):

1. **Junta** la evidencia viva de la sesión (reutiliza `TimelineRepository`, sin duplicar queries).
   Sesión vacía → `ai_no_evidence` (409).
2. **Redacta** (ADR-0005) — nunca sale un secreto crudo al proveedor.
3. **Persiste el mapeo cifrado** (ADR-0016) asociado a la sugerencia (solo si hay secretos y clave).
4. **Ensambla** el prompt con la evidencia como dato no confiable (nonce, anti-inyección).
5. **Llama** al `AIProvider` pidiendo **salida estructurada** (JSON). Modelo según `ai_policy` o `.env`.
6. **Valida la forma** (ADR-0004, `tasks.py`): si no cumple el schema → `ai_invalid_output` (502), no
   se persiste. IA no configurada → `ai_not_configured` (503); error del proveedor → `ai_provider_error`
   (502). Los tres casos **se registran** en `ai_call_log` (intento auditado).
7. **Persiste** la sugerencia en `pending` con **procedencia completa** (ADR-0003): proveedor, modelo
   **resuelto** (el que devolvió la API), versión de prompt, `ai_call_log_id` y `input_refs` (la
   evidencia usada: ids+versión). **Registra** la llamada en la bitácora.

**Procedencia y conservación (ADR-0003):** el `suggested_content` original **nunca** se sobrescribe; la
edición humana vive en `edited_content` y conserva el rastro de IA. La evidencia cruda jamás se
sustituye por la narrativa. **Máquina de estados:** `pending → accepted` | `pending|edited → edited`
(admite re-edición); `accepted` es terminal; otra transición → `ai_suggestion_invalid_transition` (409).
Cada transición guarda `reviewed_by`/`reviewed_at`.

**Cifrado del mapeo (ADR-0016):** el mapa `marcador→valor real` se cifra con **Fernet** (`crypto.py`)
y se guarda en `ai_redaction_maps` (**nunca en claro**). La clave vive en `TF_ENCRYPTION_KEY` (ver
`.env.example`; generar con `Fernet.generate_key()`). **Sin clave:** no se persiste el mapeo (seguro)
y la sugerencia queda con `redaction_map_stored=false` para que la UI avise; la generación sí funciona.

**Selección de modelo/proveedor (`ai_policy`):** `get_ai_provider` lee `projects.ai_policy` (`model`)
con `TF_ANTHROPIC_*` como fallback (hoy `ai_policy` suele venir vacía → fallback). Es la **base** de la
futura selección desde UI; no construye lógica de política compleja. Aplica también al ping de F1-T3.

## Endpoints

Ver [`../API-CONTRACT.md`](../API-CONTRACT.md) → *Gateway de IA* y *Sugerencias de IA*. Resumen:
`GET /…/ai/status` (`projects:read`), `POST /…/ai/ping` (`projects:update`; CSRF; siempre 200 con
`status`); y bajo la sesión, `POST|GET /…/sessions/{sid}/suggestions` (generar/listar) y
`POST …/suggestions/{id}/accept|edit` (transiciones). Generar/aceptar/editar → `projects:update`
(viewer no); listar → `projects:read`. La respuesta nunca expone el mapeo cifrado ni valores crudos.

## Migración

- **F1-T3** `20261105_1200-b7d9e1c4a2f5_crear_bitacora_de_llamadas_de_ia.py` (down_revision
  `9c3e71a2f4b8`). Crea `ai_call_log`. **Aplicada por el equipo** (la BD de dev está en
  `b7d9e1c4a2f5`).
- **F1-T4a** `20261106_0900-f3a1c9d7b2e4_crear_sugerencias_de_ia_y_mapeo_cifrado.py` (down_revision
  `b7d9e1c4a2f5`). **Hand-written** (create tables): crea `ai_suggestions` (CHECK nombrados de
  `kind`/`status`; FKs CASCADE en workspace/project/session, RESTRICT en `created_by`/`reviewed_by`,
  SET NULL en `ai_call_log_id`; índices de aislamiento) y `ai_redaction_maps` (mapeo cifrado; FK CASCADE
  a la sugerencia). Reversible. **Pendiente de aplicar por el equipo** (`task db-upgrade`); Claude no la
  aplica.

## Pruebas

`tests/test_ai.py` (F1-T3). **Unitarias (sin BD, sin red):** redacción de cada tipo de secreto con
marcadores estables y sin romper estructura; texto plano / IPs intactos; ensamblado que delimita la
evidencia (nonce único); `ClaudeProvider.is_configured`. **Contra la BD (doble del puerto):** el ping
en los tres estados registra en la bitácora **sin secretos**; `not_configured` no llama; viewer 403 /
no miembro 404.

`tests/test_ai_suggestions.py` (F1-T4a). **Unitarias:** cifrado round-trip (el texto cifrado no
contiene el secreto; se descifra igual) y cifrador no configurado sin clave; validación de la salida
estructurada (válida, con ```fences```, y **rechazo** de forma inválida). **Contra la BD (doble del
puerto):** generar crea `pending` con **procedencia** y la evidencia se **redacta antes de enviarse**
(se verifica con el doble que recibió texto redactado y delimitado); el mapeo se persiste **cifrado**
(y no en claro) y se puede descifrar; **sin `TF_ENCRYPTION_KEY`** la sugerencia se crea pero el mapeo
**no** se guarda (`redaction_map_stored=false`); `next_step` conserva su `rationale`; `not_configured`
(503) / salida inválida (502) / sin evidencia (409) **no** persisten sugerencia; aceptar/editar
transicionan y **conservan el original** + el rastro de IA; viewer 403 (pero lista); aislamiento 404.
**Las pruebas NUNCA llaman a la API real** (`_FakeProvider` vía `app.dependency_overrides`). Los
escenarios contra la BD se **omiten** si falta el esquema (`run_db_test(..., requires="ai_suggestions")`).

## Cómo configurar y verificar (ping y generación real)

1. En `apps/api/.env`: `TF_ANTHROPIC_API_KEY=<tu clave>` (opcional `TF_ANTHROPIC_MODEL`) y
   `TF_ENCRYPTION_KEY=<clave Fernet>` (generar con
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).
2. `task up` y aplicar las migraciones: `task db-upgrade` (la aplica **el equipo**).
3. `task dev-api`; autenticarse y crear workspace+project; **ping**: `POST …/ai/ping` (CSRF).
4. **Generación real:** crear una sesión y uno o más ítems de evidencia; luego
   `POST …/sessions/{sid}/suggestions` con `{"kind":"description"}` (CSRF). Devuelve la sugerencia
   `pending` con procedencia; con `TF_ENCRYPTION_KEY` el mapeo queda cifrado (`redaction_map_stored=true`).
   Aceptar/editar: `POST …/suggestions/{id}/accept` | `/edit`.
5. Sin `TF_ANTHROPIC_API_KEY`: la generación responde `503 ai_not_configured` (degrada). Sin
   `TF_ENCRYPTION_KEY`: la sugerencia se crea pero no se guarda el mapeo (`redaction_map_stored=false`).

## Pendiente / `[[POR LLENAR]]`

- UI y el **violeta de IA** (F1-T4b): pantallas para generar/revisar/aceptar/editar sugerencias.
- **Rehidratación efectiva**: descifrar el mapeo y mostrar valores a un usuario autorizado (hoy solo
  se persiste cifrado) + rotación de la clave (MultiFernet) — ADR-0016.
- Más funciones de IA (resumen; CVSS/CWE/CVE/ATT&CK con validación contra catálogo, F2; traducción) —
  cada una registrada en [`../ai-tasks.md`](../ai-tasks.md).
- Política de IA por proyecto (`projects.ai_policy`) completa: proveedores permitidos, imágenes,
  redacción on/off por clasificación, redacción de PII/IPs, **selección desde UI** (hoy solo se lee
  `model` con fallback al `.env`).
- `[[POR LLENAR: retención/purga de la bitácora de IA y del mapeo cifrado.]]`
