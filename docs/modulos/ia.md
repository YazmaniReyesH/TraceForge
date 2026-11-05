# Ficha de módulo: ia (gateway de IA)

- **Fase / tanda:** F1-T3 (andamiaje de IA: puerto, redacción, ensamblado, bitácora, ping)
- **Estado del módulo:** gateway `AIProvider` con Claude detrás del puerto; capa de **redacción** de
  secretos determinista; **ensamblado** de prompt con la evidencia como dato no confiable; **bitácora**
  de llamadas (`ai_call_log`); y un **ping verificable** con contenido sintético. **Sin función de
  producto** (sugerir paso / generar descripción es F1-T4), **sin UI**, **sin frontend**.
- **Última actualización:** 2026-11-05

## Propósito

Dar los cimientos para usar **IA en la nube** como motor de asistencia respetando los principios
fundacionales: la IA **propone** y el código **valida** (ADR-0004), todo contenido de IA es una
**sugerencia con procedencia** (ADR-0003), y **nada cruza el perímetro sin redacción** y auditoría
(ADR-0005). Esta tanda no implementa ninguna función de producto: prepara el puerto, la redacción, el
ensamblado anti-inyección y la bitácora, y los verifica con un ping real a Claude.

## Capas y archivos

```
app/ai/
  port.py            # Puerto AIProvider (dominio): AIPrompt, AICompletion, complete()/name/model/is_configured
  claude_provider.py # Implementación Claude (SDK anthropic, import perezoso) detrás del puerto
  errors.py          # AIError, AINotConfiguredError (503), AIProviderError (502) — sin secretos
  redaction.py       # redact(text) -> RedactionResult (texto redactado + mapa en memoria + conteo)
  prompt.py          # assemble_prompt(instruction, evidence): evidencia delimitada como dato no confiable
  schemas.py         # AIStatusRead, AIPingResult
  repository.py      # AICallLogRepository (acotado a workspace+project) — solo inserta
  service.py         # AIService: redactar → ensamblar → proveedor → bitácora (+ ping sintético)
  dependencies.py    # get_ai_provider (seleccionable), get_ai_service (sobre get_project_context)
  router.py          # /api/v1/workspaces/{wid}/projects/{pid}/ai  (GET /status, POST /ping)
app/models/
  ai_call_log.py     # AICallLog (tabla ai_call_log)
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

## Endpoints

Ver [`../API-CONTRACT.md`](../API-CONTRACT.md) → *Gateway de IA*. Resumen:
`GET /api/v1/workspaces/{wid}/projects/{pid}/ai/status` (estado de configuración; `projects:read`) y
`POST …/ai/ping` (circuito completo con contenido sintético; `projects:update`; CSRF). El ping
**siempre responde 200** con un `status` (`ok|error|not_configured`).

## Migración

- **F1-T3** `20261105_1200-b7d9e1c4a2f5_crear_bitacora_de_llamadas_de_ia.py` (down_revision
  `9c3e71a2f4b8`). **Hand-written** (create table): crea `ai_call_log` con sus FKs (CASCADE en
  workspace/project; RESTRICT en `created_by`), el CHECK nombrado de `status` y los índices de
  `workspace_id`/`project_id`. Reversible. **Pendiente de aplicar por el equipo** (`task db-upgrade`);
  Claude no la aplica.

## Pruebas

`tests/test_ai.py`. **Unitarias (sin BD, sin red):** redacción de cada tipo de secreto con marcadores
estables y sin romper estructura; texto plano / IPs intactos; ensamblado que delimita la evidencia
como dato no confiable (y nonce único por llamada); `ClaudeProvider.is_configured` desde settings.
**Contra la BD (con doble del puerto):** el circuito del ping en los tres estados (`ok` / `error` /
`not_configured`) registra en la bitácora **sin secretos crudos** (hash de 64, `redaction_count>0`,
sin la contraseña/clave sintéticas); `not_configured` no llama al proveedor; viewer no puede hacer
ping (403) pero sí leer el estado; aislamiento (no miembro → 404). **Las pruebas NUNCA llaman a la API
real:** sustituyen `get_ai_provider` por un `_FakeProvider`. Los escenarios contra la BD se **omiten**
si falta el esquema (`run_db_test(..., requires="ai_call_log")`).

## Cómo configurar y verificar el ping real

1. En `apps/api/.env`: `TF_ANTHROPIC_API_KEY=<tu clave>` (opcional `TF_ANTHROPIC_MODEL`).
2. `task up` y aplicar la migración: `task db-upgrade` (la aplica **el equipo**).
3. `task dev-api`; autenticarse y crear workspace+project; `POST …/ai/ping` con el header CSRF.
4. Sin la clave: el ping responde `status=not_configured` (degradación clara). Con la clave: `ok`,
   con la respuesta real de Claude, `redaction_count>0` y el secreto sintético enmascarado.

## Pendiente / `[[POR LLENAR]]`

- Funciones de producto de IA con procedencia y validación determinista (F1-T4): sugerir paso,
  generar descripción, resumen — cada una registrada en [`../ai-tasks.md`](../ai-tasks.md).
- Persistencia **cifrada** del mapeo marcador→valor (rehidratación) — F1-T4.
- Política de IA por proyecto (`projects.ai_policy`): proveedores permitidos, imágenes, redacción
  on/off por clasificación, redacción de PII/IPs.
- `[[POR LLENAR: retención/purga de la bitácora de IA y del mapeo cifrado.]]`
