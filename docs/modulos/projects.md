# Ficha de módulo: projects

- **Fase / tanda:** F0-T4b-2
- **Estado del módulo:** CRUD de projects + membresías de proyecto (con RBAC y aislamiento)
- **Última actualización:** 2026-10-21

## Propósito

Gestionar los **proyectos** dentro de un workspace y sus **membresías**, aplicando el núcleo de
autorización de F0-T4b-1 (contexto por ruta, rol efectivo, matriz). Cierra la Fase 0 junto con la
gestión de membresías de workspace y los invariantes protectores.

## Capas y archivos

```
app/projects/
  schemas.py       # ProjectCreate/Update/Read; ProjectMemberAdd/RoleUpdate/Read
  repository.py    # ProjectRepository(WorkspaceScopedRepository) — projects + project_memberships
  service.py       # CRUD + membresías; regla guest=viewer; mapeo IntegrityError
  dependencies.py  # get_project_repository (acotado al workspace de la ruta) / get_project_service
  router.py        # /api/v1/workspaces/{workspace_id}/projects (+ /{project_id}/members)
  errors.py        # UserNotFound, NotWorkspaceMember, GuestMustBeViewer, ProjectMemberExists
```

El `ProjectRepository` hereda de `WorkspaceScopedRepository`: todas las lecturas parten de
`scoped_select()` (filtro por `workspace_id`), de modo que el **aislamiento** es el patrón por
defecto. El `workspace_id` viene de la ruta/contexto, nunca del cliente.

## Entidades (recordatorio; esquema en `docs/modulos/modelo-base.md`)

- `projects`: `project_id`, `workspace_id` (FK, aislamiento), `name`, `classification`
  (RESERVADO), `ai_policy` (RESERVADO JSONB), timestamps.
- `project_memberships`: `project_membership_id`, `user_id`, `project_id`, `role`
  (`lead|contributor|viewer`), `created_at`. UNIQUE `(user_id, project_id)`.

`classification`/`ai_policy` se aceptan/leen (texto/JSONB) pero **sin lógica de IA** (F1).

## Reglas de acceso

- **Crear**: `projects:create` (owner/admin del workspace).
- **Listar**: cualquier miembro del workspace; owner/admin ven todos, member/guest solo los
  proyectos donde tienen membresía explícita.
- **Detalle/editar/borrar**: gate de proyecto (`projects:read`/`update`/`delete`) sobre el **rol
  efectivo** (owner/admin = piso `lead`). 404 a quien no tiene acceso efectivo; 403 a quien lo
  tiene pero su rol no permite la acción.
- **Membresías de proyecto**: `projects:manage_members` (lead). El miembro debe ser **miembro del
  workspace**; **regla dura guest=viewer**.

## Pruebas

- `test_projects.py`: CRUD (owner), aislamiento (no-miembro → 404), visibilidad por rol
  (member solo ve sus proyectos; proyecto ajeno → 404), viewer lee pero no edita/borra (403).
- `test_project_members.py`: guest=viewer (contributor/lead → 422; viewer → 201; cambio a
  contributor → 422), contributor puede editar, miembro de proyecto debe ser miembro de workspace.

## Pendiente / `[[POR LLENAR]]`

- Contenido del proyecto (evidencia, hallazgos, documentos) — fases siguientes.
- Uso real de `classification`/`ai_policy` (F1, IA).
