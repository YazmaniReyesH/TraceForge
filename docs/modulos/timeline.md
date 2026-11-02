# Ficha de módulo: timeline (sesiones y evidencia)

- **Fase / tanda:** F1-T1 (solo backend)
- **Estado del módulo:** modelo de datos + migración + CRUD mínimo append-only de sesiones e ítems
  de evidencia de texto (sin UI, sin IA)
- **Última actualización:** 2026-11-01

## Propósito

Registrar la **evidencia** de un project como una **bitácora cronológica** (timeline) de
**sesiones** que contienen **ítems de evidencia** de texto. Es el insumo crudo sobre el que se
construirán hallazgos y narrativa de IA en fases siguientes; por eso nace con **cadena de
custodia**: append-only, versionado y con hash de contenido (ADR-0012). No sustituye la evidencia
cruda por narrativa (principio fundacional, ADR-0003/0004).

## Capas y archivos

```
app/timeline/
  hashing.py       # compute_content_hash: SHA-256 del contenido canónico (ADR-0012)
  errors.py        # EvidenceKindMismatchError (evidence_kind_mismatch, 409)
  schemas.py       # SessionCreate/Update/Read; EvidenceItemCreate; *VersionRead; *Read/*DetailRead
  repository.py    # TimelineRepository(session, project_id) — acotado al project del contexto
  service.py       # reglas: append-only, hash, puntero de versión, soft-delete
  dependencies.py  # get_timeline_service (sobre get_project_context + get_session)
  router.py        # /api/v1/workspaces/{wid}/projects/{pid}/sessions (+ /{sid}/items)
app/models/
  session.py       # Session (tabla sessions)
  evidence.py      # EvidenceItem + EvidenceItemVersion (dos tablas, append-only)
```

Respeta las capas `router → service → repository`. El `TimelineRepository` se construye con el
`project_id` del **contexto de proyecto** (gate ya aplicado en el router), nunca del cliente: las
sesiones se filtran por `project_id` y los ítems/versiones por su sesión → **aislamiento** por
defecto. La identidad (`created_by`) sale del token.

## Entidades (decisiones; esquema exacto en la migración)

- **`sessions`**: `session_id` (PK), `project_id` (FK→projects, `ON DELETE CASCADE`, indexado),
  `name`, `deleted_at` (soft-delete), timestamps. Varias sesiones por project.
- **`evidence_items`** (ítem lógico, **mutable solo en metadatos**): `evidence_item_id` (PK),
  `session_id` (FK→sessions, CASCADE), `kind` (`command|note`, CHECK `ck_evidence_items_kind`),
  `position` (orden), `current_version` (puntero a la versión vigente), `deleted_at`, `created_by`
  (FK→users, `RESTRICT`), timestamps. UNIQUE `(session_id, position)`.
- **`evidence_item_versions`** (**append-only, inmutable**): `evidence_item_version_id` (PK),
  `evidence_item_id` (FK→evidence_items, CASCADE, indexado), `version`, `content_hash` (SHA-256 hex,
  64), `captured_at`, `command_text`/`command_output`/`note_text` (TEXT), `tool`/`language`
  (RESERVADO presentación, no entran al hash), `created_by` (FK→users, RESTRICT), `created_at`.
  UNIQUE `(evidence_item_id, version)`.

**Por qué dos tablas:** vuelve la inmutabilidad del contenido **física** — el contenido solo vive
en filas de versión que nunca se hacen UPDATE; el ítem lógico solo mueve su puntero y marca
`deleted_at` (ver alternativas en ADR-0012).

## Reglas de negocio

- **Append-only / versión.** Crear ítem ⇒ versión 1. "Editar" (`PATCH`) ⇒ **versión nueva** +
  `current_version++`; conserva el historial con su hash. El `kind` **no** cambia al editar →
  `evidence_kind_mismatch` (409).
- **Soft-delete.** `DELETE` marca `deleted_at`; nunca borrado físico. El ítem/sesión deja de
  listarse/leerse (404), pero la fila e historial permanecen.
- **Hash de contenido.** SHA-256 sobre bytes UTF-8 de un JSON canónico (`sort_keys`, sin espacios)
  del **contenido** (no de `tool`/`language`). Determinista y auto-verificable (ADR-0012). Lo
  calcula el backend.
- **Tope de tamaño.** Campos de texto ≤ 1 000 000 caracteres (schema, 422). Evidencia mayor →
  almacenamiento de objetos (diferido).
- **Permisos** (rol efectivo, ADR-0002): leer → `projects:read` (viewer+); escribir →
  `projects:update` (contributor/lead; owner/admin = piso lead). CSRF en mutaciones (ADR-0010).

## Endpoints

Ver [`../API-CONTRACT.md`](../API-CONTRACT.md) → *Timeline: sesiones y evidencia*. Resumen:
`POST|GET /sessions`, `PATCH|DELETE /sessions/{id}`; `POST|GET /sessions/{id}/items`,
`GET|PATCH|DELETE /sessions/{id}/items/{id}` (`GET` con `?include_history=true`).

## Migración

`migrations/versions/20261101_1854-58cdba920ffa_crear_timeline_sessions_y_evidencia_.py`
(down_revision `d587c74af99d`). Crea las tres tablas con sus FKs (CASCADE en la jerarquía
project→session→item→version; RESTRICT en `created_by`), el CHECK nombrado de `kind`, las UNIQUE y
los índices. **Pendiente de aplicar por el equipo** (`task db-upgrade`); Claude no la aplica. La
columna `kind` se crea como `VARCHAR(20)` + CHECK (mismo patrón que los roles): el autogenerate
rindió el tipo custom `StrEnumType`, se ajustó a mano a `sa.String(20)`.

## Pruebas

`tests/test_timeline.py`: hash estable e ignora `tool`/`language` (unitario); alta de sesión/ítems
y **orden** por posición; el hash del API coincide con el canónico recomputado; **editar = versión
nueva** que conserva la v1 con su hash; `kind` inmutable al editar (409); **soft-delete** (404 +
verificación en BD de que la fila persiste con `deleted_at`); **aislamiento** por project (ruta
cruzada → 404); **viewer** lee pero no escribe (403). Los escenarios contra la BD se **omiten** si
la migración aún no está aplicada (helper `run_db_test(..., requires="sessions")`).

## Pendiente / `[[POR LLENAR]]`

- UI del timeline (F1-T2); funciones de IA sobre evidencia con procedencia (F1-T3/T4).
- Evidencia binaria/archivos (almacenamiento de objetos, diferido).
- Hallazgos que referencian **versiones** de evidencia (fase futura).
- `[[POR LLENAR: política de retención/purga de evidencia borrada]]`.
