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

## Pendiente (próximas tandas)

- **F0-T5:** token anti-CSRF; theming.
- **Más adelante:** flujo de baja de cuenta (el invariante de borrado seguro ya está a nivel
  servicio); invitación por email de usuarios nuevos.
