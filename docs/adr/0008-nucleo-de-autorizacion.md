# ADR-0008: Núcleo de autorización — alcance por ruta, rol efectivo y matriz de permisos

- **Estado:** aceptado
- **Fecha:** 2026-10-21

## Contexto

F0-T4a dejó la autenticación (identidad + sesión). Ahora hace falta el **mecanismo de
autorización** que gobierne el acceso a los recursos multi-tenant del ADR-0002: resolver el
workspace de la petición, la membresía del usuario y su rol, y decidir permitir/denegar por
acción. Debe ser central, probado y reutilizable, para que F0-T4b-2 solo cuelgue de él los
endpoints de negocio y los invariantes.

Hay varias decisiones con alternativas que conviene fijar y registrar.

## Decisión

### 1. Alcance por ruta (el workspace viaja en la URL)

El `workspace_id` viaja en la **URL** (`/api/v1/workspaces/{workspace_id}/...`). La
autorización lo toma de la ruta, verifica la **membresía** del usuario autenticado y resuelve
el **rol**. **No** hay "workspace activo" por header ni por sesión.

*Por qué:* URLs explícitas, cacheables y sin estado de sesión ambiguo; cada petición dice sobre
qué workspace opera. El aislamiento se evalúa siempre en el servidor.

### 2. 404 genérico para no-miembros (no filtrar existencia)

El contexto de autorización (`get_workspace_context`) responde **404** cuando el usuario **no
tiene membresía** en el workspace de la ruta — **exista o no** el workspace. No se usa 403 para
"no miembro".

*Por qué:* un 403 "existe pero no puedes" revelaría la existencia del workspace a un extraño
(enumeración). Con 404 genérico, un no-miembro no puede distinguir "no existe" de "no soy
miembro". El **403** se reserva para un **miembro cuyo rol no permite la acción** (lo decide
`requiere_permiso`).

### 3. Rol efectivo (ADR-0002) como función pura

El cómputo del rol efectivo de proyecto es una **función pura** (`effective_project_role` en
`app/core/security.py`): para **owner/admin** el acceso implícito a todos los proyectos es un
**piso** (= `lead`) y la membresía de proyecto solo **suma**, nunca resta; para **member/guest**
el acceso proviene **solo** de la membresía explícita (sin ella, sin acceso). Completa y
cubierta por pruebas desde F0-T4b-1; su uso a nivel proyecto llega en F0-T4b-2.

### 4. Matriz de permisos central

Los permisos se definen como **matriz `rol de workspace → acciones`** en
`app/core/security.py` (fuente única), no como condicionales dispersos. `requiere_permiso(accion)`
es la dependencia que todo endpoint protegido usa; **403** si el rol no tiene la acción. (Nota:
`guest` no tiene overview del workspace — ADR-0002 —, por eso no se le concede `workspaces:read`.)

### 5. Patrón de repository con filtro por workspace

Los recursos pertenecientes a un workspace se consultan mediante un repository que **hereda de
`WorkspaceScopedRepository`** (`app/core/repository.py`), el cual impone
`WHERE workspace_id = <contexto>` en `scoped_select()`. Así el aislamiento es el patrón por
defecto y no depende de recordar el filtro en cada query. El `workspace_id` proviene del
`WorkspaceContext`, nunca del cliente.

### 6. CSRF diferido a F0-T5

Se mantiene la cookie `SameSite=Lax` y la regla **GET nunca muta**. **No** se implementa token
anti-CSRF en esta tanda; queda como ítem explícito de **F0-T5**.

### 7. Manejo de `IntegrityError` por constraint

Se sustituye el `except IntegrityError` catch-all (deuda de F0-T4a) por un **mapeo por nombre de
constraint → error de dominio** (`app/core/integrity.py` + nombres en `app/core/constraints.py`):
el registro mapea `users_email_key` → `EmailAlreadyRegisteredError`; una constraint desconocida
se **re-lanza** sin enmascarar. Helper reutilizable por F0-T4b-2 (único de membresía, índice de
owner, CHECK de roles).

## Consecuencias

**A favor:**

- Autorización central, testeable y reutilizable; aislamiento forzado por patrón; sin fuga de
  existencia de workspaces; errores de integridad precisos en vez de un 409 comodín.

**En contra / costos asumidos:**

- La resolución de membresía (gate de autz) hace **una consulta por petición** a recursos de
  workspace; se asume (es barata y va indexada por `workspace_id`/`user_id`).
- **CSRF** sigue abierto hasta F0-T5. `[[POR LLENAR: token anti-CSRF (double-submit) o
  SameSite=Strict — F0-T5]]`.
- La resolución de membresía se consulta en la capa de autorización (infraestructura
  transversal), no en un repository de dominio; es una excepción consciente al patrón
  "repository único" (el acceso a datos de negocio sí pasa por repositories).

## Alcance

F0-T4b-1 entrega el mecanismo y lo verifica con endpoints mínimos de workspaces (crear/listar/
detalle). El CRUD de projects, la gestión de membresías y los **invariantes protectores** (al
menos un owner, transferencia atómica, `guest`=viewer como regla dura, borrado seguro de
usuario) son **F0-T4b-2**.
