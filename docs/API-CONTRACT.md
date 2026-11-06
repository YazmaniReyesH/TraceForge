# API Contract — TraceForge

Contrato de negocio de la API: **permisos, reglas, ejemplos y errores** por endpoint. No
duplica el OpenAPI (firmas exactas en `/docs` y `/openapi.json`); aquí va el *porqué* y las
reglas que el OpenAPI no expresa.

Convenciones: prefijo **`/api/v1`**; cuerpos JSON; fechas en ISO-8601 UTC. La autenticación
viaja en una **cookie httpOnly** de sesión (ver ADR-0007); los endpoints también aceptan
`Authorization: Bearer <jwt>` (clientes de API / pruebas).

### Errores (envelope) — ADR-0009

Todos los errores responden con `{ "code": "...", "message": "..." }`. El **`code`** es estable
(el frontend lo mapea a i18n). Statuses: **422** validación de entrada (`validation_error`);
**409** conflicto de negocio; **403** permiso (`forbidden`); **404** no encontrado / sin acceso
(`not_found`); **401** no autenticado (`unauthenticated`). Códigos de negocio: `invalid_credentials`,
`email_already_registered`, `sole_owner`, `cannot_assign_owner`, `already_owner`, `member_exists`,
`not_a_member`, `not_workspace_member`, `guest_must_be_viewer`, `user_has_memberships`, `csrf_failed`.

### CSRF (double-submit) — ADR-0010

Toda **mutación con sesión** (POST/PATCH/DELETE) exige el header **`X-CSRF-Token`** con el valor
de la cookie legible **`tf_csrf`** (emitida en `login`, `GET /auth/me` y `GET /auth/csrf`). Sin
coincidencia → **403** `csrf_failed`. Los **GET nunca mutan** y no se validan. `login`/`register`
están **exentos** (arranque, pre-sesión); `logout` **sí** exige CSRF.

---

## Autenticación — `/api/v1/auth` (F0-T4a)

Identidad y sesión. La **autorización fina** (RBAC, workspace activo, rol) llega en F0-T4b; por
ahora ningún endpoint resuelve permisos de workspace/proyecto.

> Nota anti-enumeración: `login` nunca revela si el email existe; `register` usa un mensaje de
> error genérico. El email se normaliza (minúsculas + trim) antes de registrar/buscar.

### POST `/api/v1/auth/register`
- **Permiso:** público (sin sesión).
- **Cuerpo:** `{ "email": "<email>", "password": "<min 8, max 128>", "display_name": "<1..200>" }`
- **201** → `UserRead` `{ user_id, email, display_name, created_at }` (sin `password_hash`).
- **Errores:** `422` validación (email inválido, password corta, display_name vacío);
  `409` `{"detail":"No se pudo completar el registro"}` si el email ya existe (mensaje genérico).
  > Deuda conocida: el **código 409** permite enumeración de usuarios por registro; se cerrará con
  > verificación por email (ver ADR-0007).
- **Ejemplo:**
  ```http
  POST /api/v1/auth/register
  {"email":"ana@acme.com","password":"Sup3r-Secret-Pw!","display_name":"Ana"}
  → 201 {"user_id":"…","email":"ana@acme.com","display_name":"Ana","created_at":"…"}
  ```

### POST `/api/v1/auth/login`
- **Permiso:** público.
- **Cuerpo:** `{ "email": "<email>", "password": "<str>" }`
- **200** → `UserRead` y **Set-Cookie** `tf_session=<jwt>` (httpOnly, SameSite=Lax, Secure en prod).
- **Errores:** `401` `{"detail":"Credenciales inválidas"}` si el email no existe **o** la
  contraseña es incorrecta (mismo mensaje, sin enumeración); `422` validación.
- **Nota:** email case-insensitive (`Ana@ACME.com` === `ana@acme.com`). Emite además la cookie
  CSRF `tf_csrf` (ADR-0010).

### POST `/api/v1/auth/logout`
- **Permiso:** sesión + **CSRF** (`X-CSRF-Token`). Idempotente.
- **204** sin cuerpo; borra las cookies `tf_session` y `tf_csrf`.
- **Errores:** `403` `csrf_failed` si falta/no coincide el token CSRF.
- **Nota:** el JWT es stateless; el token sigue válido hasta expirar (sin revocación aún — ver
  ADR-0007).

### GET `/api/v1/auth/me`
- **Permiso:** autenticado (cookie `tf_session` o `Authorization: Bearer`).
- **200** → `UserRead`; **renueva** la cookie `tf_csrf` (para hidratar la sesión en la SPA).
- **Errores:** `401` `{"code":"unauthenticated"}` si falta el token, es inválido o expiró.

### GET `/api/v1/auth/csrf`
- **Permiso:** público. **204**; emite/renueva la cookie `tf_csrf`. Útil para obtener un token
  antes de una mutación.

---

## Workspaces — `/api/v1/workspaces` (F0-T4b-1)

Alcance por ruta: el `workspace_id` viaja en la URL. Autorización: **404** a no-miembros (no
filtra existencia); **403** a miembro cuyo rol no permite la acción (ver ADR-0008). Matriz de
permisos en `docs/modulos/autorizacion.md`.

### POST `/api/v1/workspaces`
- **Permiso:** autenticado (cualquier usuario con sesión).
- **Cuerpo:** `{ "name": "<1..200>" }`
- **201** → `WorkspaceRead` `{ workspace_id, name, created_at }`. El creador queda **owner**
  (membresía creada en la misma transacción).
- **Errores:** `401` sin sesión; `422` validación.

### GET `/api/v1/workspaces`
- **Permiso:** autenticado. Devuelve **solo** los workspaces donde el usuario tiene membresía
  (aislamiento: no incluye ajenos).
- **200** → `[WorkspaceRead]`. **401** sin sesión.

### GET `/api/v1/workspaces/{workspace_id}`
- **Permiso:** miembro del workspace con `workspaces:read` (owner/admin/member; **no** guest).
- **200** → `WorkspaceRead`.
- **Errores:** `401` sin sesión; `404` si no eres miembro o el workspace no existe (mismo
  cuerpo, sin filtrar existencia); `403` si eres miembro pero tu rol no puede leer (p. ej. guest).

### PATCH `/api/v1/workspaces/{workspace_id}` (F0-T5b)
- **Permiso:** `workspaces:update` (owner/admin). CSRF.
- **Cuerpo:** `{ "name": "<1..200>" }`. **200** → `WorkspaceRead`.
- **Errores:** `403` `forbidden`; `404` no miembro / no existe; `422` validación.

### DELETE `/api/v1/workspaces/{workspace_id}` (F0-T5b)
- **Permiso:** `workspaces:delete` (**solo owner**). CSRF.
- **Borrado PROTEGIDO** (ADR-0011): solo si el workspace **no tiene projects** y su **único
  miembro es el owner**. **204** si se elimina.
- **Errores:** `403` `forbidden` (no owner); `409` `workspace_not_empty` (tiene projects u otros
  miembros); `404` no miembro / no existe.

### Membresías de workspace — `/api/v1/workspaces/{workspace_id}/members` (F0-T4b-2)

- **GET** — listar miembros. Permiso `workspaces:read`. 200 → `[WorkspaceMemberRead]`.
- **POST** `{ "email", "role": admin|member|guest }` — añadir un usuario **existente**. Permiso
  `workspaces:manage_members`. 201 → `WorkspaceMemberRead`. Errores: `404` email no existe; `409`
  ya es miembro; `409` si `role=owner` (el owner se asigna por transferencia).
  `[[POR LLENAR: invitación por email de usuarios nuevos]]`.
- **PATCH** `/{user_id}` `{ "role" }` — cambiar rol. Permiso `workspaces:manage_members`. 200.
  Errores: `404` no es miembro; `409` si `role=owner`; `409` si intentas degradar al **único
  owner** (transfiere primero).
- **DELETE** `/{user_id}` — quitar miembro (y sus membresías de proyecto en el workspace).
  Permiso `workspaces:manage_members`. 204. Error `409` si es el **único owner**.
- **POST** `/api/v1/workspaces/{workspace_id}/transfer-ownership` `{ "new_owner_user_id" }` —
  transferencia **atómica** (nuevo→owner, anterior→admin). Permiso
  `workspaces:transfer_ownership` (**solo owner**). 204. Errores: `404` el nuevo owner no es
  miembro; `409` si ya es owner.

---

## Projects — `/api/v1/workspaces/{workspace_id}/projects` (F0-T4b-2)

Gate de proyecto (ADR-0008): **404** si el proyecto no existe, no pertenece al workspace o el
usuario no tiene **acceso efectivo** (member/guest sin membresía de proyecto); **403** si tiene
acceso pero su rol efectivo no permite la acción. owner/admin tienen piso implícito = `lead`.

- **POST** `{ "name", "classification"? }` — crear. Permiso `projects:create` (owner/admin).
  201 → `ProjectRead`. (`classification`/`ai_policy` reservados; sin lógica de IA.)
- **GET** — listar. Miembro del workspace. owner/admin ven **todos**; member/guest **solo** los
  proyectos donde son miembros. 200 → `[ProjectRead]`.
- **GET** `/{project_id}` — detalle. Permiso `projects:read` (lead/contributor/viewer). 200 /
  404 / 403.
- **PATCH** `/{project_id}` `{ "name"?, "classification"? }` — editar. Permiso `projects:update`
  (lead/contributor). 200 / 404 / 403.
- **DELETE** `/{project_id}` — borrar. Permiso `projects:delete` (lead). 204 / 404 / 403.

### Membresías de proyecto — `.../projects/{project_id}/members`

- **GET** — listar. Permiso `projects:read`. 200 → `[ProjectMemberRead]`.
- **POST** `{ "email", "role": lead|contributor|viewer }` — añadir **miembro del workspace** al
  proyecto. Permiso `projects:manage_members` (lead). 201. Errores: `404` email no existe (`user_not_found`);
  `409` `not_workspace_member` si el usuario no es miembro del workspace; `409` **regla dura
  guest=viewer** (`guest_must_be_viewer`); `409` `member_exists`.
- **PATCH** `/{user_id}` `{ "role" }` — cambiar rol. Permiso `projects:manage_members`. 200 /
  404 / `409` (`guest_must_be_viewer`).
- **DELETE** `/{user_id}` — quitar. Permiso `projects:manage_members`. 204 / 404.

---

## Vistas del usuario — `/api/v1/me` (F0-T5b)

Vistas **transversales** acotadas al usuario autenticado (solo sesión; **sin** `requiere_permiso`
de workspace). No filtran nada que el usuario no pueda ver ya.

### GET `/api/v1/me/projects`
- **Permiso:** autenticado. Devuelve los proyectos accesibles por el usuario a través de **todos**
  sus workspaces: los de workspaces donde es **owner/admin** (acceso implícito a todos sus
  projects) **unidos** a los projects donde tiene **membresía de proyecto** explícita (member/guest).
- **200** → `[MyProjectRead]` = `{ project_id, name, workspace_id, workspace_name, role, created_at }`,
  donde `role` es el **rol efectivo** del usuario sobre el project (ADR-0002; owner/admin ⇒ `lead`).
  Ordenado por `workspace_name`, `created_at`. **401** sin sesión.
- **Ejemplo:** un `guest` que es `viewer` de un solo project ve **solo** ese project (no los demás
  del workspace); un `member` sin membresía de proyecto ve `[]`.
- **Uso en UI:** pantalla "Mis proyectos", para que un guest llegue a su project sin entrar al
  workspace (no tiene `workspaces:read`).

---

## Timeline: sesiones y evidencia — `.../projects/{project_id}/sessions` (F1-T1)

Bitácora cronológica de evidencia dentro de un project. **Append-only y versionada** (ADR-0012):
"editar" crea una **versión nueva** conservando el historial con su hash; "borrar" es
**soft-delete**. La evidencia es de **texto** (F1): `kind` `command` (comando + output) o `note`
(texto libre). Todo cuelga del **gate de proyecto** (acceso y aislamiento ya resueltos por la ruta:
un `session_id`/`item_id` de otro project ⇒ **404**). Mutaciones exigen **CSRF** (ADR-0010).

- **Permisos:** leer → `projects:read` (viewer+); crear/editar/borrar → `projects:update`
  (contributor/lead; owner/admin del workspace tienen piso `lead`, ADR-0002).
- **Hash:** `content_hash` es SHA-256 del contenido canónico (ver ADR-0012); lo calcula el backend,
  el cliente no lo envía. `tool`/`language` son pistas de presentación y **no** entran en el hash.
- **Tope:** cada campo de texto ≤ **1 000 000** caracteres (`422` si se excede).

### Sesiones — `.../sessions`

- **POST** `{ "name": "<1..200>" }` — crear sesión. `projects:update`. **201** → `SessionRead`
  `{ session_id, project_id, name, created_at, updated_at }`.
- **GET** — listar sesiones vivas del project (orden por `created_at`). `projects:read`. **200** →
  `[SessionRead]`.
- **PATCH** `/{session_id}` `{ "name" }` — renombrar. `projects:update`. **200** / **404**.
- **DELETE** `/{session_id}` — **soft-delete** (marca `deleted_at`; no borra). `projects:update`.
  **204** / **404**. (La FK a `evidence_items` es `ON DELETE CASCADE` como red del esquema, pero el
  servicio no borra físicamente.)

### Ítems de evidencia — `.../sessions/{session_id}/items`

- **POST** `{ "kind": "command"|"note", "command_text"?, "command_output"?, "note_text"?, "tool"?, "language"?, "captured_at"?, "after_item_id"? }`
  — añade un ítem y crea su **versión 1**. `projects:update`. **201** → `EvidenceItemRead`. Reglas:
  `command` exige `command_text`; `note` exige `note_text` (si no → `422`). `captured_at` por
  defecto = ahora (UTC). **Orden (ADR-0013):** sin `after_item_id` (o `null`) **añade al final**
  (caso por defecto); con `after_item_id = <id>` **inserta justo después** de ese ítem (posiciones
  con huecos; renumeración automática si se agota el hueco). El cliente nunca envía `position`.
- **GET** — listar ítems vivos **en orden** (`position`), cada uno con su **versión vigente**
  (`current`). `projects:read`. **200** → `[EvidenceItemRead]`.
- **GET** `/{item_id}?include_history=<bool>` — detalle del ítem con su versión vigente; con
  `include_history=true` agrega `history` (todas las versiones, orden ascendente). `projects:read`.
  **200** → `EvidenceItemRead` | `EvidenceItemDetailRead`. **404** si no existe / borrado.
- **PATCH** `/{item_id}` (mismo cuerpo que POST; `after_item_id` **se ignora** aquí) — **edición =
  versión NUEVA** (append-only); mueve `current_version` y conserva las anteriores. El `kind`
  **debe coincidir** con el del ítem (si no → **409** `evidence_kind_mismatch`). `projects:update`.
  **200** → `EvidenceItemRead`.
- **PATCH** `/{item_id}/move` `{ "after_item_id": <uuid>|null }` — **reordena** el ítem (ADR-0013):
  `null` = al inicio; un id = justo después de ese ítem; al final = id del último. **Solo cambia el
  orden**: no crea versión ni altera el `content_hash` (append-only intacto). `projects:update`.
  **200** → `EvidenceItemRead`. **404** si el ítem o el `after_item_id` no existen en la sesión
  (aislamiento). Mover un ítem después de sí mismo es no-op.
- **DELETE** `/{item_id}` — **soft-delete**. `projects:update`. **204** / **404**.

**Formas de respuesta** (negocio; firmas exactas en OpenAPI):
- `EvidenceItemRead` = `{ evidence_item_id, session_id, kind, position, current_version, created_by, created_at, current: EvidenceItemVersionRead }`.
- `EvidenceItemVersionRead` = `{ evidence_item_version_id, version, content_hash, captured_at, command_text, command_output, tool, language, note_text, created_by, created_at }`.
- `EvidenceItemDetailRead` = `EvidenceItemRead` + `{ history: [EvidenceItemVersionRead] }`.

---

## Gateway de IA — `/api/v1/workspaces/{wid}/projects/{pid}/ai` (F1-T3)

Andamiaje de IA (ADR-0003/0004/0005, ADR-0015). **Aún sin función de producto** (sugerir paso /
generar descripción es F1-T4): solo estado y un **ping verificable**. Ambos bajo el **gate de
proyecto** (aislamiento por workspace/project) y **CSRF** en mutaciones. El modelo y la API key salen
de configuración (`TF_ANTHROPIC_*`), nunca del cliente. Ver ficha [`modulos/ia.md`](./modulos/ia.md).

### GET `/ai/status`
- **Permiso:** `projects:read` (viewer+). **No** llama al proveedor ni cuesta.
- **200** → `{ "configured": <bool>, "provider": "claude", "model": "<modelo>" }`.
  `configured=false` cuando falta `TF_ANTHROPIC_API_KEY`.

### POST `/ai/ping`
- **Permiso:** `projects:update` (contributor/lead; owner/admin = piso lead). Hace una llamada
  **real y de pago** al proveedor y **registra** en la bitácora. **CSRF** obligatorio. Sin cuerpo
  (el contenido es **sintético**, fijado en el servidor: incluye un secreto falso y un intento de
  inyección falso).
- Ejecuta el circuito completo: **redacta** → **ensambla** (evidencia delimitada como dato no
  confiable) → **llama** a Claude (si hay key) → **registra** en `ai_call_log`.
- **Siempre 200** (es un diagnóstico: reporta el estado del circuito, no es el circuito). El campo
  `status` dice qué pasó:
  - `ok` — el proveedor respondió; `response_text` trae la respuesta de Claude y los tokens.
  - `not_configured` — no hay API key: **no** se llamó al proveedor (degradación clara);
    `response_text=null`.
  - `error` — error de red/API del proveedor (traducido, sin secretos); `error_code` lo identifica
    (p. ej. `ai_provider_error`); `response_text=null`.
- **200** → `AIPingResult` = `{ ai_call_log_id, status, configured, provider, model,
  redaction_count, redacted_evidence, assembled_user_prompt, response_text, input_tokens,
  output_tokens, error_code }`. Todo lo devuelto es **seguro** (ya redactado): `redacted_evidence`
  prueba que la redacción corrió; `assembled_user_prompt` muestra la evidencia delimitada.
- **403** si viewer (solo lee estado, no hace ping). **404** si no es miembro del project (aislamiento).

**Qué guarda la bitácora** (`ai_call_log`, ADR-0015): proveedor, modelo, estado, tokens, el prompt
**ya redactado** + su SHA-256, el conteo de redacciones, `error_code`, usuario y workspace/project.
**Nunca** el contenido sin redactar, el mapeo marcador→valor, ni la API key.

---

## Sugerencias de IA — `.../projects/{pid}/sessions/{sid}/suggestions` (F1-T4a)

Primera función de IA **de producto** (ADR-0003/0004/0005/0016): a partir de la evidencia **real** de
una sesión, la IA **propone** una `description` o un `next_step`. Toda sugerencia nace **`pending`**
(ADR-0003) con procedencia completa; un humano la **acepta** o la **edita**. Bajo el **gate de
proyecto** (aislamiento) y **CSRF** en mutaciones. El modelo se elige de la `ai_policy` del proyecto
si está, con `TF_ANTHROPIC_*` como fallback. La respuesta **nunca** expone el mapeo cifrado ni valores
crudos. Ver ficha [`modulos/ia.md`](./modulos/ia.md) y [`ai-tasks.md`](./ai-tasks.md).

### POST `/suggestions`
- **Permiso:** `projects:update` (contributor/lead; viewer no). **CSRF.** Hace una llamada **real y de
  pago** al proveedor.
- **Cuerpo:** `{ "kind": "description" | "next_step" }`.
- Circuito: junta la evidencia de la sesión → **redacta** (ADR-0005) → **persiste el mapeo cifrado**
  (ADR-0016; solo si hay secretos y clave) → **ensambla** (evidencia como dato no confiable) → **llama**
  pidiendo **salida estructurada** → **valida la forma** (ADR-0004) → persiste en `pending` con
  procedencia → **registra** en `ai_call_log` (F1-T3).
- **201** → `AISuggestionRead` (ver forma abajo).
- **409 `ai_no_evidence`** si la sesión no tiene evidencia. **502 `ai_invalid_output`** si el modelo
  devolvió una forma inválida (no se persiste). **502 `ai_provider_error`** ante error de red/API.
  **503 `ai_not_configured`** si falta `TF_ANTHROPIC_API_KEY` (degrada; registra el intento). **403**
  viewer. **404** si no es miembro del project o la sesión no existe (aislamiento).

### GET `/suggestions`
- **Permiso:** `projects:read` (viewer+). Lista las sugerencias de la sesión (orden de creación).
- **200** → `[AISuggestionRead]`.

### POST `/suggestions/{suggestion_id}/accept`
- **Permiso:** `projects:update`. **CSRF.** Transición **`pending` → `accepted`** (toma la sugerencia
  tal cual). Registra `reviewed_by`/`reviewed_at`.
- **200** → `AISuggestionRead`. **409 `ai_suggestion_invalid_transition`** si no estaba `pending`
  (p. ej. ya aceptada/editada). **404** si no existe en esa sesión/project.

### POST `/suggestions/{suggestion_id}/edit`
- **Permiso:** `projects:update`. **CSRF.** Transición **`pending`|`edited` → `edited`**: guarda el
  texto humano en `edited_content` **conservando** el `suggested_content` original y el rastro de
  origen IA. `accepted` es terminal (no se edita).
- **Cuerpo:** `{ "content": "<texto>" }`.
- **200** → `AISuggestionRead`. **409 `ai_suggestion_invalid_transition`** si estaba `accepted`.
  **404** si no existe.

**Forma de respuesta** `AISuggestionRead` = `{ ai_suggestion_id, session_id, kind, status,
suggested_content, suggested_payload, edited_content, provider, model, prompt_version, ai_call_log_id,
input_refs, redaction_count, redaction_map_stored, reviewed_by, reviewed_at, created_by, created_at,
updated_at }`. `suggested_content` (texto propuesto, inmutable) y `suggested_payload` (salida
estructurada validada) son **seguros** (se generaron sobre evidencia redactada). `redaction_map_stored`
es `false` si no hubo secretos **o** si faltaba `TF_ENCRYPTION_KEY` (degradación segura, ADR-0016).

---

## Pendiente (próximas tandas)

- **F0-T5:** token anti-CSRF; theming.
- **F1:** funciones **de producto** de IA sobre evidencia con procedencia (F1-T4, sobre el gateway de
  F1-T3); evidencia binaria/archivos (almacenamiento de objetos, diferido); hallazgos que referencian
  **versiones** de evidencia; política de retención/purga de evidencia borrada y de la bitácora de IA.
- **Más adelante:** flujo de baja de cuenta (el invariante de borrado seguro ya está a nivel
  servicio); invitación por email de usuarios nuevos.
