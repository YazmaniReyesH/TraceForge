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

## Gate y matriz de PROYECTO (F0-T4b-2)

- `get_project_context` combina el rol de workspace + el rol de proyecto con
  `effective_project_role`. **404** si el proyecto no existe, no pertenece al workspace o el
  usuario no tiene acceso efectivo (member/guest sin membresía); **403** (vía
  `requiere_permiso_proyecto`) si tiene acceso pero su rol efectivo no permite la acción.
- `PROJECT_PERMISSION_MATRIX` (rol de proyecto → acciones):

| Acción | lead | contributor | viewer |
|---|:---:|:---:|:---:|
| `projects:read` | ✓ | ✓ | ✓ |
| `projects:update` | ✓ | ✓ | — |
| `projects:delete` | ✓ | — | — |
| `projects:manage_members` | ✓ | — | — |

`projects:create` es acción de **workspace** (owner/admin). owner/admin tienen piso efectivo =
`lead` en cualquier proyecto.

## Manejo de `IntegrityError` por constraint

`app/core/integrity.py` (`constraint_name`, `translate_integrity_error`) + nombres en
`app/core/constraints.py`. Mapea constraint → error de dominio; desconocida → re-lanza. Usado en
registro (`users_email_key`), alta de miembro de workspace (`uq_workspace_memberships_user_workspace`)
y de proyecto (`uq_project_memberships_user_project`).

## Endpoints

Ver `docs/API-CONTRACT.md`: workspaces (+ `/members`, `/transfer-ownership`) y projects
(+ `/{project_id}/members`). Ficha de projects: `docs/modulos/projects.md`.

## Invariantes de SERVICIO (F0-T4b-2, implementados y probados)

- **Al menos un owner**: no se puede degradar ni quitar al único owner (`CannotModifySoleOwnerError`).
- **Transferencia atómica**: nuevo→owner / anterior→admin en una tx (degrada, `flush`, promueve;
  respeta el índice único parcial de owner).
- **`owner` no se asigna directamente** (add/change): `CannotAssignOwnerRoleError`.
- **`guest` = solo `viewer`** como regla dura en el servicio de membresías de proyecto
  (`GuestMustBeViewerError`).
- **Rol efectivo** aplicado en el gate de proyecto.
- **Borrado seguro de usuario** (`app/users/`): un user con membresías no se borra
  (`UserHasMembershipsError`); respeta el `ON DELETE RESTRICT`. **No hay endpoint de baja aún.**

## Pendiente / `[[POR LLENAR]]`

- **CSRF** (token double-submit o `SameSite=Strict`) — **F0-T5** (ADR-0008).
- **Invitación por email** de usuarios nuevos (hoy solo se añaden usuarios existentes).
- **Flujo completo de baja de cuenta** (endpoint + revocar membresías / transferir titularidades).
