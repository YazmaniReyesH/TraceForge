# CLAUDE.md — TraceForge

Reglas globales del proyecto para Claude Code (y guía rápida para el equipo). Si
una skill de `.claude/skills/` y este archivo se contradicen, **detente y pregunta**.

## Qué es TraceForge

Plataforma de **documentación técnica para TI / Ciberseguridad** (pentest, CTF,
auditoría, BCP/DRP, arquitecturas cloud, procesos, etc.) con **IA en la nube** como
motor de asistencia. Multiusuario desde el inicio, con tema claro/oscuro (theming en
tandas posteriores). Slug corto para paquetes/código: **`tf`**.

Repositorio: https://github.com/YazmaniReyesH/TraceForge.git

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python **3.12** + FastAPI + Pydantic v2 + **SQLAlchemy 2 (async) + Alembic** |
| Gestor backend | **uv** (gestiona también el Python 3.12) |
| Frontend | React + TypeScript + **Vite** + **PrimeReact**; TanStack Query, react-router, i18next (es-MX), tipos desde OpenAPI |
| Gestor frontend | **npm** |
| Base de datos | **PostgreSQL 16 + pgvector**, acceso async con **asyncpg** (ver ADR-0001) |
| Infra de dev | **Docker Compose** (`compose.yaml`): db + **Redis 7** (Redis disponible, aún sin uso en código). **MinIO/almacenamiento: diferido** — deuda conocida |
| Orquestación dev | **go-task** (`Taskfile.yml`) — fuente única de verdad, local y CI |

> **Dev contra la infra en contenedores:** el backend y el frontend corren en el
> **host** (uv/npm), pero el backend se conecta a la **PostgreSQL de los contenedores**.
> Por eso `task dev-api` requiere `task up` antes. (Contenerizar api/web es de una fase
> posterior: el perfil `prod` queda preparado en `compose.yaml`.)

> Principios de IA (fundacionales, ver skill `backend-fastapi`): (1) todo contenido
> de IA es una **sugerencia con procedencia** que nace "pendiente"; (2) la **IA
> propone y el código determinista valida/calcula**. La evidencia cruda nunca se
> sustituye por narrativa generada y se redactan secretos antes de salir a un proveedor.

## Estructura del monorepo

```
TraceForge/
  apps/
    api/        # Backend FastAPI (uv)
      app/
        main.py              # app FastAPI + /health + routers (auth, workspaces)
        core/config.py       # Settings (pydantic-settings, prefijo TF_; DB/Redis/S3/auth)
        core/db.py           # engine async + sessionmaker + Base + get_session
        core/security.py     # autorización (F0-T4b-1): matriz, rol efectivo, contexto, requiere_permiso
        core/repository.py   # WorkspaceScopedRepository (filtro por workspace)
        core/integrity.py    # mapeo IntegrityError -> error de dominio (por constraint)
        core/constraints.py  # nombres de constraints centralizados
        models/              # SQLAlchemy: user, workspace, project, membership, credential, session, evidence, ai_call_log, enums, types
        ai/                  # gateway de IA (F1-T3): port AIProvider + Claude, redacción, ensamblado anti-inyección, bitácora, ping
        auth/                # autenticación (F0-T4a): port AuthProvider + local, hashing, tokens, service, router
        workspaces/          # workspaces + membresías e invariantes de owner (F0-T4b): repo, service, router, schemas
        projects/            # CRUD de projects + membresías de proyecto (F0-T4b-2)
        timeline/            # sesiones + evidencia append-only (F1-T1): hashing, repo, service, router, schemas
        users/               # borrado seguro de usuario (invariante; sin endpoint de baja)
      migrations/            # Alembic (async); versions/ con migraciones F0-T3b, F0-T4a, F1-T1, F1-T2 y F1-T3
      tests/
      alembic.ini
      pyproject.toml         # deps + ruff + mypy + pytest
      .python-version        # 3.12
    web/        # Frontend React + Vite + TS (npm); Vite proxya /api -> backend en dev
      src/
        main.tsx · App.tsx     # providers (Theme/Query/Router/PrimeReact) + rutas (páginas lazy)
        shared/theme/          # tokens.css (FUENTE ÚNICA; incl. --code-*/--term-* del timeline), ThemeProvider
        shared/api/            # cliente HTTP (CSRF, 401, errores), types.gen.ts (OpenAPI)
        shared/i18n/           # es-MX (sin textos hardcodeados) · shared/ui/ (layout, loader, estados)
        modules/auth/          # login/register/logout, guard, hooks
        modules/workspaces/ · modules/projects/   # pantallas de dominio (lista+detalle, miembros)
        modules/me/            # vista transversal "Mis proyectos" (/projects)
        modules/timeline/      # timeline de evidencia (F1-T2): sesiones, captura, arrastre, historial, Prism lazy
  packages/
    shared/     # (placeholder) cliente TS generado desde OpenAPI — aún vacío
  docs/
    adr/        # ADRs individuales (contexto → decisión → consecuencias)
    arquitectura.md  # índice de ADRs + panorama
    GITHUB_WORKFLOW.md  # flujo Git/PR del proyecto
    modulos/    # fichas de módulo (_plantilla.md)
    # (en tandas futuras: API-CONTRACT.md, ai-tasks.md, plantillas.md,
    #  seguridad-datos.md, glosario.md)
  .claude/skills/   # skills del proyecto (NO tocar sin acuerdo)
  .github/workflows/ci.yml
  compose.yaml · Taskfile.yml · .dockerignore
  CLAUDE.md · README.md · .editorconfig · .gitignore · .pre-commit-config.yaml
```

## Comandos de desarrollo

Requiere **go-task** instalado (Windows: `winget install Task.Task` · macOS:
`brew install go-task/tap/go-task` · Linux: instalador oficial), más **uv** y **npm**.

Requiere además **Docker** (Desktop/Engine) para la infra.

| Comando | Qué hace |
|---|---|
| `task setup` | Instala dependencias de `api` (uv) y `web` (npm) desde cero |
| `task up` | Levanta la infra en contenedores (db, redis) |
| `task down` | Detiene la infra (conserva los datos) |
| `task down-v` | Detiene la infra y **borra los volúmenes/datos** |
| `task db-shell` | Abre `psql` dentro del contenedor de Postgres |
| `task dev-api` | Levanta la API en http://127.0.0.1:8000 (`/health`, `/health/ready`, `/docs`) — **requiere `task up`** |
| `task dev-web` | Levanta el frontend en http://127.0.0.1:5173 |
| `task lint` | ruff (backend) + eslint/prettier (frontend) |
| `task typecheck` | mypy (backend) + tsc (frontend) |
| `task test` | pytest (backend) |
| `task build-web` | Build de producción del frontend (lo que valida CI) |
| `task db-revision -- "msg"` | **Genera** una migración Alembic (la revisa/aplica el equipo) |
| `task db-upgrade` | Aplica migraciones (`alembic upgrade head`) — **la ejecuta el equipo** |
| `task gen-types` | Regenera los tipos TS del frontend desde el OpenAPI del backend (commitear) |
| `task --list` | Ver todas las tareas |

Primer arranque: `task setup`, copiar `apps/api/.env.example`→`.env` y
`apps/web/.env.example`→`.env`, `task up` (espera a que la infra esté saludable),
luego `task dev-api` y `task dev-web`.

> **Dos `.env` que deben coincidir:** `apps/api/.env` lo lee el backend
> (`TF_DATABASE_URL`) y un `.env` en la **raíz** lo lee compose para crear la base
> (`TF_DB_USER`/`TF_DB_PASSWORD`/`TF_DB_NAME`; opcional, con valores por defecto). Las
> credenciales de la base deben ser las mismas en ambos o el backend no conecta.

## Documentación viva

La documentación vive en `docs/` y se actualiza en el **mismo PR** que el código
(skill `documentacion-proyecto`). Convención de **ADRs** (decisiones de arquitectura):

- **Un ADR por archivo** en `docs/adr/NNNN-titulo.md`, numeración consecutiva, con el
  formato **contexto → decisión → consecuencias** (ver `docs/adr/README.md`).
- **`docs/arquitectura.md`** es el **índice y la visión general**: enlaza a cada ADR y
  da el panorama de la arquitectura. No duplica el contenido de los ADR.
- Un ADR no se reescribe cuando cambia la realidad: se marca como *reemplazado* y se
  crea uno nuevo que lo supera.

El **flujo de trabajo Git/PR** del proyecto (rama por tanda, commits, PR, merge) está
en [`docs/GITHUB_WORKFLOW.md`](./docs/GITHUB_WORKFLOW.md).

El **contrato de negocio de la API** (permisos, reglas, ejemplos, errores por endpoint)
está en [`docs/API-CONTRACT.md`](./docs/API-CONTRACT.md).

Otros documentos de `docs/` (se crean cuando la tanda correspondiente los necesita):
`plantillas.md`, `glosario.md` y las fichas de `docs/modulos/<modulo>.md` (desde `_plantilla.md`). Ya
existen: `seguridad-datos.md`, `ai-tasks.md` (registro de funciones de IA), `modulos/modelo-base.md`,
`modulos/auth.md`, `modulos/autorizacion.md`, `modulos/projects.md`, `modulos/frontend.md`,
`modulos/timeline.md`, `modulos/ia.md`.

## Convención de trabajo (obligatoria)

- **Planear primero**, implementar en **tandas pequeñas** con **pausas de validación**.
  Al terminar una tanda, Claude se detiene y muestra el resultado para que el equipo
  valide antes de continuar.
- **Claude Code NO hace git**: nada de `git add/commit/push` ni crear PRs. Eso lo hace
  el equipo.
- **Claude Code NO aplica migraciones ni accede a la base de datos.** Cuando toque,
  Claude **genera** la migración (Alembic) y la deja lista y comentada; **el equipo
  revisa el SQL y la aplica** (`alembic upgrade head`). El esquema jamás se cambia a
  mano en la base.
- Si una decisión no es obvia, **preguntar antes de asumir**.
- **Un cambio sin su documentación actualizada NO está terminado**: el código y su
  documentación viajan en el **mismo PR** (skill `documentacion-proyecto`).

## Skills del proyecto (`.claude/skills/`)

| Skill | Cuándo se usa |
|---|---|
| **documentacion-proyecto** | SIEMPRE al cerrar una tarea y antes de un PR: mantiene viva la documentación de `docs/` (ADRs, API-CONTRACT, fichas de módulo, ai-tasks, plantillas, seguridad-datos, glosario). |
| **backend-fastapi** | Al escribir/modificar backend: endpoints, servicios, repositorios, modelos, schemas, RBAC, aislamiento por workspace, auditoría y funciones de IA. Hace respetar las capas router→service→repository y los principios de IA. |
| **frontend-react** | SIEMPRE al escribir/modificar frontend: pantallas, componentes, formularios, tablas, layout, tema claro/oscuro, tokens, cliente HTTP, sesión/errores, i18n, tipos desde OpenAPI, RBAC de UX. Fuente de verdad de la identidad visual y los patrones de pantalla. |
| **nuevo-modulo** | Al iniciar un módulo/fase/pantalla nuevos: crea el **andamiaje** (esqueleto con TODOs) parejo en back y front. No implementa lógica de negocio. |
| **migraciones-postgresql** | Al cambiar el esquema (tablas, columnas, índices, FKs, CHECKs, JSONB/pgvector). Claude genera y revisa la migración; **el equipo la aplica**. |
| **revision-modulo** | "Definición de Terminado" antes de cerrar un módulo o abrir su PR: capas, modelo de datos, seguridad multiusuario, IA, pruebas, migraciones y documentación. |

## Convenciones de código (resumen)

- **Backend**: capas `router → service → repository`; respuestas con schemas `XxxRead`;
  identidad/rol y `workspace_id` salen del **token**, nunca del cliente; estados como
  `StrEnum` + CHECK nombrado; `ruff` + `mypy` (estricto) + `pytest` en verde.
- **Frontend**: TypeScript estricto, ESLint + Prettier; sin `any` injustificado;
  manejar estados de carga/error/vacío.
- **Documentación en español**, explicando el *porqué*. Marcar lo no resuelto como
  `[[POR LLENAR: ...]]`, nunca inventarlo.

## Estado actual

**Fase 1 EN CURSO. F1-T3 (andamiaje de IA: gateway, redacción, ensamblado, bitácora — solo backend).**
Puerto **`AIProvider`** (dominio, patrón port/adapter como `AuthProvider`) con **Claude** detrás (SDK
`anthropic`, import perezoso; "IA no configurada" degrada sin romper). Capa de **redacción**
determinista de secretos (marcadores estables, preserva estructura; PEM/JWT/`sk-`/`AKIA`/`Bearer`/
asignaciones/ hashes; **PII/IPs fuera por defecto**). **Ensamblado** de prompt con la evidencia como
**dato no confiable** (frontera con nonce, anti-inyección). **Bitácora** `ai_call_log` (qué se envió
**ya redactado** + SHA-256 + conteo; nunca el crudo, el mapeo ni la key; aislamiento por workspace/
project). **Ping** verificable `POST …/ai/ping` (contenido sintético; siempre 200 con `status`
ok/error/not_configured) y `GET …/ai/status`. Modelo/clave por settings (`TF_ANTHROPIC_*`, por
defecto `claude-sonnet-4-5`). **Sin función de producto (F1-T4), sin UI, sin frontend.** **Migración
F1-T3 generada, sin aplicar** (`b7d9e1c4a2f5`: crea `ai_call_log`). Pruebas con **doble del puerto**
(no llaman a la API real). Ver `docs/modulos/ia.md`, `docs/ai-tasks.md`, `docs/API-CONTRACT.md`,
`docs/seguridad-datos.md`, ADR-0015.

**F1-T2 (timeline: reordenar/insertar + UI).** Checkpoint 1 (backend): orden por
**posiciones con huecos** (múltiplos de ~1000; ADR-0013) con **índice no único** y orden determinista
`(position, created_at, id)`; `POST /items` acepta `after_item_id` (insertar "entre dos"; sin él,
append) y `PATCH /items/{id}/move` (reordenar: `null`=inicio, id=después); reordenar **no versiona**
ni toca hashes (append-only, ADR-0012); renumeración en dos fases al agotar un hueco. **Migración
F1-T2 aplicada por el equipo** (`9c3e71a2f4b8`: quita UNIQUE + backfill + índice no único).
Checkpoint 2 (frontend): **pantalla de timeline** (módulo `modules/timeline`) estilo consola de
operador con riel/glow, bloque de comando tipo terminal, **resaltado de sintaxis lazy** (Prism,
ADR-0014), notas, telemetría en mono, captura ágil con scanline, **reordenar/insertar por arrastre**
(optimista), historial con hash y `prefers-reduced-motion`; **code-splitting** de rutas (chunk
principal ~780→~427 kB, sin aviso > 500 kB). Ver `docs/modulos/timeline.md`, `docs/modulos/frontend.md`,
`docs/API-CONTRACT.md`, ADR-0013/0014.

**F1-T1 (timeline: modelo de evidencia, solo backend):** modelo de **sesiones** e
**ítems de evidencia** de texto (`command`/`note`) **append-only y versionados** con SHA-256 por
versión y **soft-delete** (cadena de custodia, ADR-0012); dos tablas (ítem lógico mutable +
versiones inmutables). CRUD mínimo bajo el gate de proyecto
(`/api/v1/workspaces/{wid}/projects/{pid}/sessions` + `/items`): leer→`projects:read`,
escribir→`projects:update`; aislamiento por project; CSRF en mutaciones. **Migración generada, sin
aplicar** (`58cdba920ffa`, la aplica el equipo). Sin UI ni IA (F1-T2/T3/T4). Ver
`docs/modulos/timeline.md`, `docs/API-CONTRACT.md`, ADR-0012.

**Fase 0 COMPLETA. F0-T5b (pantallas de dominio + edición/borrado de workspace + "Mis
proyectos"):** UI de **workspaces** (lista+detalle, crear/editar/eliminar con borrado protegido) y
**projects** (CRUD), **gestión de miembros** de ambos y **transferencia de propiedad**, con patrón
lista+detalle, permisos como UX (rol derivado de miembros + `/auth/me`), errores por `code` (i18n),
confirmaciones y ambos temas. Vista transversal **"Mis proyectos"** (`/projects`) desde
`GET /api/v1/me/projects` (salida de navegación del guest), **degradación amable del 403** del
detalle de workspace (enlace a Mis proyectos) y fix de contraste del dropdown de rol. Backend:
`PATCH`/`DELETE /workspaces/{id}` (borrado **protegido**: `409 workspace_not_empty`, ADR-0011) y
`GET /api/v1/me/projects` (solo auth). **Sin migración.** Ver `docs/modulos/frontend.md`,
`docs/modulos/autorizacion.md`, `docs/API-CONTRACT.md`, ADR-0011.

Hecho en F0-T5a: envelope de errores `{code,message}` (ADR-0009), CSRF double-submit (ADR-0010),
cimientos de UI (tema por tokens sin parpadeo, i18n es-MX, cliente HTTP, flujo de auth, tipos
OpenAPI, proxy de Vite).

Hecho en Fase 0 (T4b): modelo base + RBAC multiusuario + invariantes de servicio (al menos un
owner, transferencia atómica, guest=viewer, borrado seguro de usuario). Ver ADR-0002/0006/0008.

**Pendiente (post-Fase 0 / F1+):** invitación por email; borrado de workspace con contenido;
`SameSite=Strict`; baja de cuenta; code-splitting del bundle; evidencia/hallazgos/documentos e IA.

Hecho en F0-T4b-1: núcleo de autorización (contexto por ruta, rol efectivo, matriz,
`requiere_permiso`, `WorkspaceScopedRepository`, mapeo de `IntegrityError`) y endpoints mínimos
de workspaces (ADR-0008).

Hecho en F0-T4a: autenticación local (argon2id + JWT en cookie httpOnly) tras `AuthProvider`,
tabla `user_credentials`, endpoints `/auth/*`, `get_current_user` (ADR-0007).

Hecho en F0-T3b: modelo base (users, workspaces, projects, membresías) con aislamiento e
invariantes de esquema y su 1ª migración (ADR-0002/0006).

Hecho en F0-T2: `compose.yaml` (Postgres 16+pgvector, Redis), backend async a Postgres,
`GET /health/ready`, Alembic async, CI con service container.

> **Deuda conocida — MinIO/almacenamiento diferido:** en 2025 MinIO retiró sus
> imágenes community de Docker Hub y su registro (quay.io) exige autenticación, por lo
> que no se fijó una imagen. Como MinIO no se usa en código aún, `minio`/`minio-init`
> quedan **comentados** en `compose.yaml` y las variables `TF_S3_*` quedan reservadas.
> Se retomará (eligiendo imagen/registro) al implementar el almacenamiento real.

Hecho en F0-T1: monorepo uv+npm, `GET /health`, frontend que lo consume, go-task, CI,
pre-commit.
