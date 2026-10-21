# TraceForge

Plataforma de **documentación técnica para TI / Ciberseguridad** (pentest, CTF,
auditoría, BCP/DRP, arquitecturas cloud, procesos) con **IA en la nube** como motor
de asistencia. Multiusuario, con tema claro/oscuro (en tandas posteriores).

Monorepo: backend FastAPI (uv) + frontend React/Vite (npm), orquestado con **go-task**.

## Requisitos

- [uv](https://docs.astral.sh/uv/) — gestiona el backend y Python 3.12.
- [Node.js](https://nodejs.org/) 20+ y npm — frontend.
- [go-task](https://taskfile.dev/installation/) — orquestación (`task`).
  - Windows: `winget install Task.Task`
  - macOS: `brew install go-task/tap/go-task`
  - Linux: ver instalador oficial de taskfile.dev.

## Arranque rápido

```bash
# 1. Instalar dependencias de backend y frontend
task setup

# 2. Variables de entorno (copiar los ejemplos)
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env

# 3. Levantar backend y frontend (en dos terminales)
task dev-api    # http://127.0.0.1:8000  (GET /health, /docs)
task dev-web    # http://127.0.0.1:5173
```

Abre http://127.0.0.1:5173: la página consulta `GET /health` del backend y muestra
el estado (`ok` + versión).

## Comandos

| Comando | Qué hace |
|---|---|
| `task setup` | Instala dependencias de api (uv) y web (npm) |
| `task dev-api` / `task dev-web` | Levanta backend / frontend |
| `task lint` | ruff + eslint/prettier |
| `task typecheck` | mypy + tsc |
| `task test` | pytest |
| `task --list` | Todas las tareas |

## Estructura

```
apps/api      Backend FastAPI (uv) — GET /health en F0-T1
apps/web      Frontend React + Vite + TS (npm)
packages/shared  Cliente TS desde OpenAPI (placeholder)
docs/         ADRs y fichas de módulo (documentación viva)
.claude/skills   Skills del proyecto
```

## Cómo trabajamos

Se desarrolla en **tandas pequeñas con validación**. Convención completa, stack y
mapa de skills en [`CLAUDE.md`](./CLAUDE.md). Puntos clave: la documentación viaja en
el mismo PR que el código; las migraciones las revisa y aplica el equipo.

## Estado

**F0-T1:** andamiaje del monorepo + `/health` + frontend que lo consume + go-task +
CI + pre-commit. Docker y PostgreSQL llegan en **F0-T2**.
