# Ficha de módulo: auth

- **Fase / tanda:** F0-T4a
- **Estado del módulo:** autenticación e identidad (sin RBAC fino, que es F0-T4b)
- **Última actualización:** 2026-10-21

## Propósito

Permitir que un usuario se **registre** e **inicie sesión**, y dejar un **contexto de sesión**
del que F0-T4b resuelva el usuario autenticado. Autenticación **local** (email + contraseña,
argon2id + JWT) detrás del puerto de dominio `AuthProvider`, para sumar SSO más adelante sin
reescribir. Decisiones en **ADR-0007**. Endpoints en **docs/API-CONTRACT.md**.

## Modelo de credenciales

- Tabla **`user_credentials`** (aparte de `users`, ver ADR-0007):
  - `user_credential_id` UUID PK (`default=uuid4`).
  - `user_id` UUID **FK → users** `ON DELETE CASCADE`, **UNIQUE** (una credencial local por usuario).
  - `password_hash` TEXT NOT NULL (argon2id; **nunca** en claro, logs ni schemas).
  - `created_at` / `updated_at` timestamptz.
- Migración incremental: `20261021_2003-d587c74af99d_crear_tabla_user_credentials_auth_local.py`
  (`down_revision = 46e44e47a038`). **Pendiente de aplicar por el equipo** (`task db-upgrade`).

## Puerto `AuthProvider` y capas

```
router (HTTP)  ->  service (normaliza, commit, emite token)  ->  AuthProvider (puerto)
                                                                     └─ LocalAuthProvider
                                                                          └─ repository (users/credenciales)
```

- **`app/auth/port.py`** — `AuthProvider` (ABC): `register(...)`, `authenticate(...)`. Un
  **SSO futuro** es otra implementación de esta interfaz (resuelve identidad por claims, sin
  contraseña); el service y los endpoints no cambian.
- **`app/auth/local_provider.py`** — `LocalAuthProvider`: usa repository + hasher. En
  `authenticate`, si el usuario no existe hace **verificación señuelo** (anti-enumeración por
  temporización).
- **`app/auth/repository.py`** — único acceso a BD (`users` + `user_credentials`).
- **`app/auth/service.py`** — `AuthService`: **normaliza el email** (minúsculas + trim), llama
  al provider, hace **commit**, y emite el JWT en login. Traduce carrera de UNIQUE a
  `EmailAlreadyRegisteredError`.
- **`app/auth/router.py`** — delgado; traduce errores de dominio a HTTP; set/clear de la cookie.
- **`app/auth/hashing.py`** — `Argon2Hasher` (argon2id, coste configurable).
- **`app/auth/tokens.py`** — `create_access_token` / `decode_access_token` (JWT HS256).
- **`app/auth/dependencies.py`** — wiring + `get_current_user` (401 si falta/invalido).

## Flujo de token

- JWT **HS256**; `sub = user_id`; `exp` configurable (`TF_JWT_EXPIRES_MINUTES`); secreto
  `TF_JWT_SECRET` (el de dev es inseguro a propósito).
- Transporte: **cookie httpOnly** `tf_session` (SameSite=Lax; Secure en prod) emitida en
  `/login`, borrada en `/logout`. `get_current_user` también acepta `Authorization: Bearer`.
- **Frontend esperado (no construido aquí):** `login`/`register` por fetch con
  `credentials: "include"`; la cookie se envía sola; `/auth/me` para hidratar la sesión; manejar
  401 redirigiendo a login. (Pantallas: fase de frontend.)

## Normalización de email

- Se normaliza en el **servicio** (`strip().lower()`) antes de registrar/buscar. Se eligió
  normalizar en servicio (una forma canónica única) frente a índice funcional/`citext`, por
  simplicidad y portabilidad; el `UNIQUE` de BD sigue sobre el valor guardado (ya normalizado).

## Enum `role` (cierre de nota F0-T3b)

- Se añadió `StrEnumType` (`app/models/types.py`), un `TypeDecorator` cuyo impl es `String`: las
  lecturas de `role` devuelven el `StrEnum` y no `str` plano. **No cambia el tipo de columna**
  (sigue `VARCHAR(20)`), por lo que **no requiere migración** (verificado: el autogenerate no
  produce diff en `role`).

## Configuración (settings `TF_…`)

`TF_JWT_SECRET`, `TF_JWT_ALGORITHM` (HS256), `TF_JWT_EXPIRES_MINUTES`, `TF_AUTH_COOKIE_NAME`,
`TF_AUTH_COOKIE_SECURE`, `TF_AUTH_COOKIE_SAMESITE`, `TF_ARGON2_TIME_COST`,
`TF_ARGON2_MEMORY_COST`, `TF_ARGON2_PARALLELISM`.

## Pruebas (`tests/test_auth.py`)

Registro ok (sin exponer hash); login ok + cookie + `/me`; password incorrecta → 401 genérico;
email desconocido → mismo 401; email duplicado → 409; email case-insensitive; `/me` sin token /
con token inválido → 401; logout → 204. Requieren el esquema de auth aplicado (si no, se omiten).

## Pendiente (F0-T4b o posterior)

- RBAC (`requiere_permiso`), workspace activo y rol efectivo; invariantes de servicio de
  membresías; endpoints de workspaces/projects/memberships.
- `[[POR LLENAR]]`: estrategia CSRF (double-submit vs SameSite=Strict); revocación de tokens /
  refresh; verificación por email (anti-enumeración real en registro). Ver ADR-0007.
