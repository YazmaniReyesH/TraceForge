# Ficha de módulo: autorizacion

- **Fase / tanda:** F0-T4b-1
- **Estado del módulo:** núcleo de autorización + endpoints mínimos de workspaces
- **Última actualización:** 2026-10-21

## Propósito

Mecanismo de autorización multi-tenant (ADR-0002, ADR-0008): resolver el workspace de la ruta,
la membresía y el rol del usuario, y permitir/denegar por acción con una matriz central. Se
verifica con endpoints mínimos de workspaces. El CRUD de projects, la gestión de membresías y
los invariantes protectores son **F0-T4b-2**.

## Contexto de autorización (`app/core/security.py`)

- **Alcance por ruta:** el `workspace_id` viaja en la URL; `get_workspace_context(workspace_id,
  user, session)` verifica la membresía y devuelve `WorkspaceContext(user, workspace_id,
  workspace_role)`.
- **404 genérico a no-miembros:** si no hay membresía (exista o no el workspace) → **404**, para
  no filtrar la existencia. El **403** se reserva para un miembro cuyo rol no permite la acción.
- La consulta de membresía (gate de autz) vive en la capa de autorización (infraestructura), no
  en un repository de dominio; el acceso a datos de negocio sí pasa por repositories.

## Rol efectivo (`effective_project_role`, función pura)

| workspace_role | project_role | efectivo |
|---|---|---|
| owner / admin | cualquiera o ninguno | **lead** (piso implícito; solo suma) |
| member | contributor/viewer | ese rol de proyecto |
| member | — (sin membresía) | **sin acceso** (None) |
| guest | viewer | viewer |
| guest | — | sin acceso |

Se usa a nivel proyecto en F0-T4b-2; ya está completa y probada.

## Matriz de permisos (`PERMISSION_MATRIX`)

Fuente única `rol de workspace → acciones` (sin ifs dispersos). Acciones actuales (`Permission`):

| Acción | owner | admin | member | guest |
|---|:---:|:---:|:---:|:---:|
| `workspaces:read` | ✓ | ✓ | ✓ | — |
| `workspaces:update` | ✓ | ✓ | — | — |
| `workspaces:manage_members` | ✓ | ✓ | — | — |
| `workspaces:delete` | ✓ | — | — | — |

`guest` no tiene overview del workspace (ADR-0002): sin permisos a nivel workspace. La matriz se
ampliará en F0-T4b-2 (projects, memberships, …).

## `requiere_permiso(accion)`

Dependencia FastAPI que usa el contexto + la matriz: **403** si el rol no tiene la acción. Todo
endpoint protegido de recurso de workspace nace con ella. En el router se instancia como
singleton de módulo (`_requiere_lectura = requiere_permiso(Permission.WORKSPACES_READ)`).

## Patrón de filtro por workspace (`app/core/repository.py`)

`WorkspaceScopedRepository` (base): define `model` (con columna `workspace_id`) y
`scoped_select()` que ya impone `WHERE workspace_id = <contexto>`. Los repos de recursos de
workspace (projects, evidencia, … en F0-T4b-2+) heredan de aquí para que el aislamiento sea el
patrón por defecto. El `workspace_id` proviene del `WorkspaceContext`, nunca del cliente.

## Manejo de `IntegrityError` por constraint

`app/core/integrity.py` (`constraint_name`, `translate_integrity_error`) + nombres en
`app/core/constraints.py`. Mapea constraint → error de dominio; desconocida → re-lanza. Aplicado
al registro (`users_email_key` → `EmailAlreadyRegisteredError`). F0-T4b-2 añadirá los mapeos de
membresía/owner/CHECK.

## Endpoints (ver `docs/API-CONTRACT.md`)

- `POST /api/v1/workspaces` — crear (auth); el creador queda **owner** (misma transacción).
- `GET /api/v1/workspaces` — listar los del usuario (aislamiento).
- `GET /api/v1/workspaces/{workspace_id}` — detalle (`requiere_permiso(workspaces:read)`).

## Invariantes de SERVICIO pendientes (F0-T4b-2)

- **Al menos un owner** por workspace; **transferencia atómica** de propiedad.
- **`guest` = solo `viewer`** como **regla dura** en el servicio (rechazar guest+contributor/lead).
- **Borrado seguro de usuario** (limpiar membresías ante el `ON DELETE RESTRICT`).
- CRUD de projects y **gestión de membresías** (añadir/quitar/cambiar rol) con su RBAC.
- Rol efectivo a **nivel proyecto** usando `effective_project_role`.

## Pendiente / `[[POR LLENAR]]`

- **CSRF** (token double-submit o `SameSite=Strict`) — **F0-T5** (ADR-0008).
