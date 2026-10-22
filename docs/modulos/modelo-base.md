# Ficha de módulo: modelo_base

- **Fase / tanda:** F0-T3b
- **Estado del módulo:** andamiaje de datos (modelos + primera migración; sin service/endpoints)
- **Última actualización:** 2026-10-21

## Propósito

Materializa las cinco entidades base del inquilinato y el control de acceso de TraceForge
(ADR-0002): identidad de usuarios, workspaces (inquilino), proyectos y las dos membresías.
Aquí viven **solo los modelos SQLAlchemy y la primera migración**, con el aislamiento por
workspace y los invariantes que son de **nivel de esquema**. Los schemas Pydantic, el
repository, el service (con los invariantes de servicio) y los endpoints son de **F0-T4**.

Decisiones de modelado: identificadores en inglés `snake_case`; PK `UUID` generada en la app
(`default=uuid4`); enums como `VARCHAR + CHECK` con nombre (no enum nativo); fechas
`timestamptz`. Borrado y unicidad de owner: ver **ADR-0006**.

## Entidades, columnas, enums, CHECKs e índices

### `users` — identidad global a la instancia
| Columna | Tipo | Notas |
|---|---|---|
| `user_id` | UUID | **PK**, `default=uuid4` |
| `email` | VARCHAR(320) | **UNIQUE** en toda la instancia, NOT NULL (normalización: F0-T4) |
| `display_name` | VARCHAR(200) | NOT NULL |
| `created_at` / `updated_at` | timestamptz | NOT NULL, `server_default now()`; `updated_at` con `onupdate` |

### `workspaces` — el inquilino (tope de la jerarquía)
| Columna | Tipo | Notas |
|---|---|---|
| `workspace_id` | UUID | **PK**, `default=uuid4` |
| `name` | VARCHAR(200) | NOT NULL |
| `ai_policy` | JSONB | **nullable — RESERVADO** (techo de política de IA, ADR-0005; sin uso en código) |
| `created_at` / `updated_at` | timestamptz | NOT NULL |

### `projects` — unidad de trabajo dentro de un workspace
| Columna | Tipo | Notas |
|---|---|---|
| `project_id` | UUID | **PK**, `default=uuid4` |
| `workspace_id` | UUID | **FK → workspaces**, NOT NULL, **índice** (`ix_projects_workspace_id`), `ON DELETE CASCADE` |
| `name` | VARCHAR(200) | NOT NULL |
| `classification` | VARCHAR(50) | **nullable — RESERVADO** (niveles TBD en F1; **sin CHECK** todavía) |
| `ai_policy` | JSONB | **nullable — RESERVADO** (política por proyecto, ADR-0005) |
| `created_at` / `updated_at` | timestamptz | NOT NULL |

### `workspace_memberships` — pertenencia user ↔ workspace
| Columna | Tipo | Notas |
|---|---|---|
| `workspace_membership_id` | UUID | **PK**, `default=uuid4` |
| `user_id` | UUID | **FK → users**, NOT NULL, `ON DELETE RESTRICT` |
| `workspace_id` | UUID | **FK → workspaces**, NOT NULL, **índice**, `ON DELETE CASCADE` |
| `role` | VARCHAR(20) | NOT NULL, **CHECK** `ck_workspace_memberships_role` |
| `created_at` | timestamptz | NOT NULL |

- **Enum `WorkspaceRole`**: `owner`, `admin`, `member`, `guest`.
- **UNIQUE** `uq_workspace_memberships_user_workspace` (`user_id`, `workspace_id`).
- **Índice único PARCIAL** `uq_workspace_memberships_single_owner` sobre (`workspace_id`)
  **`WHERE role = 'owner'`** → **un solo owner por workspace**.

### `project_memberships` — pertenencia user ↔ project
| Columna | Tipo | Notas |
|---|---|---|
| `project_membership_id` | UUID | **PK**, `default=uuid4` |
| `user_id` | UUID | **FK → users**, NOT NULL, `ON DELETE RESTRICT` |
| `project_id` | UUID | **FK → projects**, NOT NULL, **índice**, `ON DELETE CASCADE` |
| `role` | VARCHAR(20) | NOT NULL, **CHECK** `ck_project_memberships_role` |
| `created_at` | timestamptz | NOT NULL |

- **Enum `ProjectRole`**: `lead`, `contributor`, `viewer`.
- **UNIQUE** `uq_project_memberships_user_project` (`user_id`, `project_id`).

## Relaciones y borrado (ON DELETE) — ver ADR-0006

- `workspaces` 1—N `projects` (CASCADE) · `workspaces` 1—N `workspace_memberships` (CASCADE).
- `projects` 1—N `project_memberships` (CASCADE).
- `users` 1—N `workspace_memberships` / `project_memberships` (**RESTRICT**: no se borra un user
  con membresías; el borrado seguro es un flujo de servicio en F0-T4+).
- **Nota:** no se definieron `relationship()` ORM en esta tanda (no las necesita el esquema ni
  las pruebas). Se añadirán en F0-T4 cuando el service navegue el grafo.

## Aislamiento

Todo `project` lleva `workspace_id` NOT NULL + índice: es la columna por la que el repository
filtrará siempre (F0-T4). Las membresías cuelgan de workspace/project; el acceso efectivo se
resolverá en el service según ADR-0002.

## Invariantes de SERVICIO pendientes (F0-T4)

El esquema cubre "como máximo un owner", unicidad de membresías y validez de rol. **Faltan**,
como lógica de servicio (no de esquema):

- **"Al menos un owner"** por workspace (el índice parcial solo cubre el "como máximo uno").
- **Transferencia atómica de propiedad** (nuevo owner sube / anterior baja a admin en una tx).
- **`guest` = solo `viewer`**: rechazar `guest` + (`contributor`|`lead`) como regla dura.
- **Rol efectivo** (owner/admin = piso; member/guest solo por membresía explícita).
- **Borrado seguro de usuario** (limpiar membresías / resolver titularidad ante el `RESTRICT`).
- Normalización de `email` (p. ej. a minúsculas) antes de persistir.

## Migración

- Revisión: `20261021_1908-46e44e47a038_crear_modelo_base_users_workspaces_.py`
  (mensaje: "crear modelo base: users, workspaces, projects y membresías").
- Incluye las 5 tablas, los CHECK con nombre, las UNIQUE, el **índice parcial de owner** y los
  índices de FKs; `downgrade` revierte en orden inverso.
- **Pendiente de aplicar por el equipo:** revisar el SQL y ejecutar `task db-upgrade`
  (`alembic upgrade head`). Claude Code **no** la aplica.

## Pruebas

`tests/test_model_invariants.py` verifica a nivel de BD: email duplicado, segundo owner en el
mismo workspace, membresía de workspace duplicada y membresía de proyecto duplicada. Requieren
el esquema aplicado (en local `task up` + `task db-upgrade`; en CI, service container +
`task db-upgrade`); si no está aplicado, se **omiten** en vez de fallar.
