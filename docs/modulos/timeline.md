# Ficha de módulo: timeline (sesiones y evidencia)

- **Fase / tanda:** F1-T1 (modelo) · F1-T2 (reordenar/insertar + **UI del timeline**)
- **Estado del módulo:** modelo + CRUD append-only de sesiones e ítems de evidencia de texto, con
  inserción "entre dos" y reordenamiento por posiciones espaciadas, y la **pantalla del timeline**
  (captura, arrastre, historial, realce semántico, layout de dos columnas) en frontend. Sin IA.
- **Última actualización:** 2026-11-05

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
  `position` (orden en **escala con huecos**, ADR-0013), `current_version` (puntero a la versión
  vigente), `deleted_at`, `created_by` (FK→users, `RESTRICT`), timestamps. **Índice NO único**
  `ix_evidence_items_session_position (session_id, position)` (antes era UNIQUE; ver ADR-0013).
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
- **Orden con huecos (ADR-0013).** `position` en múltiplos de ~1000 (`POSITION_STEP`). Añadir al
  final = `max+STEP`. Insertar "entre dos" = punto medio entre vecinos; si no cabe un intermedio,
  se **renumera** la sesión (en dos fases, rango negativo→final, para no colisionar) y se recalcula.
  Orden determinista `(position, created_at, evidence_item_id)`. La API usa **vecindad**
  (`after_item_id`), nunca `position`.
- **Reordenar no versiona.** Mover un ítem (`PATCH .../move`) cambia solo `position`; **no** crea
  versión ni altera hashes (append-only intacto).
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
`POST|GET /sessions`, `PATCH|DELETE /sessions/{id}`; `POST|GET /sessions/{id}/items`
(`POST` acepta `after_item_id` para insertar), `GET|PATCH|DELETE /sessions/{id}/items/{id}`
(`GET` con `?include_history=true`) y `PATCH /sessions/{id}/items/{id}/move` (reordenar).

## Migraciones

- **F1-T1** `20261101_1854-58cdba920ffa_crear_timeline_sessions_y_evidencia_.py`
  (down_revision `d587c74af99d`). Crea las tres tablas con sus FKs (CASCADE en la jerarquía
  project→session→item→version; RESTRICT en `created_by`), el CHECK nombrado de `kind`, las UNIQUE y
  los índices. La columna `kind` se crea como `VARCHAR(20)` + CHECK (el autogenerate rindió el tipo
  custom `StrEnumType`, se ajustó a mano a `sa.String(20)`).
- **F1-T2** `20261102_1030-9c3e71a2f4b8_evidencia_posiciones_con_huecos.py`
  (down_revision `58cdba920ffa`). **Hand-written** (cambio de constraint + backfill de datos):
  quita el `UNIQUE(session_id, position)`, **rellena** las posiciones existentes a la escala con
  huecos (`1000·n` por sesión, en el orden actual) y crea el índice **no único**
  `ix_evidence_items_session_position`. `downgrade` reconstruye posiciones contiguas 0-based y
  restaura el `UNIQUE` (reversible).

**Pendiente de aplicar por el equipo** (`task db-upgrade`); Claude no las aplica. La BD de dev ya
está en F1-T1 (`58cdba920ffa`); falta aplicar F1-T2 (`9c3e71a2f4b8`).

## Pruebas

`tests/test_timeline.py`. **Unitarias (sin BD):** hash estable e ignora `tool`/`language`;
aritmética de huecos `_midpoint` (punto medio, fin de zona, agotamiento). **Contra la BD:** alta de
sesión/ítems y orden; hash del API == canónico; **editar = versión nueva** que conserva la v1 con su
hash; `kind` inmutable al editar (409); **soft-delete** (404 + fila persiste con `deleted_at`);
aislamiento por project (404); viewer lee pero no escribe (403). **Reordenar/insertar (F1-T2):**
insertar "entre dos" deja el orden correcto **sin tocar hashes ni versiones** de los vecinos; mover
reordena sin crear versión; **agotar huecos dispara renumeración controlada** (todo en verde, orden
sano); viewer no puede reordenar (403); mover por ruta de otro project → 404. Los escenarios contra
la BD se **omiten** si falta el esquema (helper `run_db_test(..., requires="sessions")`).

## Frontend (F1-T2)

La **UI del timeline** (módulo `apps/web/src/modules/timeline/`) consume estos endpoints: pantalla
dentro del project (layout de dos columnas, sidebar sticky) con lista de sesiones + timeline de la
sesión activa, captura ágil (barra compacta) de command/note, reordenar/insertar por **arrastre**
(optimista, vía `after_item_id`), copiar por sección (comando/salida/nota), historial de versiones
con hash corto, y resaltado de sintaxis cargado **lazy** (Prism, ADR-0014). Dirección visual,
tokens y verificación manual: ver [`frontend.md`](./frontend.md) → *Timeline de evidencia*.

### Realce semántico de entidades de seguridad (frontend, determinista)

Capa de realce **determinista por regex** (NO IA, NO un lenguaje de Prism) que se aplica **al comando
y a la salida** y toma cada entidad como una **unidad** (una IP completa, que Prism partiría en los
puntos). Convive con Prism: el texto se parte en `[entidad | resto]`; la entidad se envuelve con una
clase `--sem-*` y Prism resalta solo el "resto" (`apps/web/src/modules/timeline/components/semantic.ts`
y `highlight.ts`). Colores por tokens `--sem-*` (claro/oscuro) y peso 600 como pista secundaria (el
color no es el único indicador). Prioridad por orden (específico → genérico) para evitar solapes:

| Entidad | Patrón (resumen) | Token/clase |
|---|---|---|
| CVE | `CVE-\d{4}-\d{4,}` | `--sem-cve` |
| Hash | hex de 64 / 40 / 32 (`sha256`/`sha1`/`md5`) | `--sem-hash` |
| IPv6 | formas completas y comprimidas con `::` | `--sem-ip` |
| IPv4 (+CIDR) | octetos `0–255`, `/NN` opcional | `--sem-ip` |
| Puerto | `\d{1,5}/(tcp\|udp\|sctp)` | `--sem-port` |
| Estado | `open` / `closed` / `filtered` | `--sem-state-open\|closed\|filtered` |
| Ruta | ruta absoluta Unix, ≥2 segmentos | `--sem-path` |

Es síncrono (sin lazy) para la salida; para el comando se pinta semántico al instante y se **mejora**
con Prism al cargar. Mantiene el fallback a texto plano. Decisión contenida al frontend (alternativa
descartada: reescribir el stream de tokens de Prism); no ameritó ADR propio (el de resaltado es
ADR-0014).

## Pendiente / `[[POR LLENAR]]`

- UI del timeline (F1-T2); funciones de IA sobre evidencia con procedencia (F1-T3/T4).
- Evidencia binaria/archivos (almacenamiento de objetos, diferido).
- Hallazgos que referencian **versiones** de evidencia (fase futura).
- `[[POR LLENAR: política de retención/purga de evidencia borrada]]`.
