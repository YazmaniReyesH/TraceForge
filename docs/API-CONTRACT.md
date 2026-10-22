# API Contract — TraceForge

Contrato de negocio de la API: **permisos, reglas, ejemplos y errores** por endpoint. No
duplica el OpenAPI (firmas exactas en `/docs` y `/openapi.json`); aquí va el *porqué* y las
reglas que el OpenAPI no expresa.

Convenciones: prefijo **`/api/v1`**; cuerpos JSON; fechas en ISO-8601 UTC. La autenticación
viaja en una **cookie httpOnly** de sesión (ver ADR-0007); los endpoints también aceptan
`Authorization: Bearer <jwt>` (clientes de API / pruebas).

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
- **Nota:** email case-insensitive (`Ana@ACME.com` === `ana@acme.com`).

### POST `/api/v1/auth/logout`
- **Permiso:** público/idempotente (no exige token válido).
- **204** sin cuerpo; borra la cookie `tf_session`.
- **Nota:** el JWT es stateless; el token sigue válido hasta expirar (sin revocación aún — ver
  ADR-0007).

### GET `/api/v1/auth/me`
- **Permiso:** autenticado (cookie `tf_session` o `Authorization: Bearer`).
- **200** → `UserRead` del usuario autenticado.
- **Errores:** `401` `{"detail":"No autenticado"}` si falta el token, es inválido o expiró.

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

---

## Pendiente (próximas tandas)

- **F0-T4b-2:** endpoints de `projects` / `memberships` (añadir/quitar/cambiar rol) con RBAC y
  aislamiento; invariantes protectores (al menos un owner, transferencia atómica, guest=viewer).
- **F0-T5:** token anti-CSRF.
