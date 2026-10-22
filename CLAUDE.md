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
| Frontend | React + TypeScript + **Vite** |
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
        main.py              # app FastAPI + GET /health (liveness) + /health/ready
        core/config.py       # Settings (pydantic-settings, prefijo TF_; DB/Redis/S3)
        core/db.py           # engine async + sessionmaker + Base + get_session
      migrations/            # Alembic (async); versions/ vacío hasta F0-T3
      tests/
      alembic.ini
      pyproject.toml         # deps + ruff + mypy + pytest
      .python-version        # 3.12
    web/        # Frontend React + Vite + TS (npm)
      src/      # main.tsx, App.tsx (consume /health), api.ts
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

Otros documentos de `docs/` (se crean cuando la tanda correspondiente los necesita):
`API-CONTRACT.md`, `ai-tasks.md`, `plantillas.md`, `seguridad-datos.md`, `glosario.md`
y las fichas de `docs/modulos/<modulo>.md` (desde `_plantilla.md`).

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

**F0-T2 (infra de datos):** `compose.yaml` con PostgreSQL 16+pgvector y Redis
(puertos en 127.0.0.1, healthchecks, volúmenes); backend conectado a Postgres (async
asyncpg) con `GET /health/ready`; Alembic async configurado (sin migraciones aún);
CI con service container de Postgres. **Sin** modelos de datos ni migraciones,
autenticación/RBAC, uso real de Redis, contenerización de api/web, IA ni theming
(tandas posteriores).

> **Deuda conocida — MinIO/almacenamiento diferido:** en 2025 MinIO retiró sus
> imágenes community de Docker Hub y su registro (quay.io) exige autenticación, por lo
> que no se fijó una imagen. Como MinIO no se usa en código aún, `minio`/`minio-init`
> quedan **comentados** en `compose.yaml` y las variables `TF_S3_*` quedan reservadas.
> Se retomará (eligiendo imagen/registro) al implementar el almacenamiento real.

Hecho en F0-T1: monorepo uv+npm, `GET /health`, frontend que lo consume, go-task, CI,
pre-commit.
