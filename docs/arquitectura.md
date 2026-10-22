# Arquitectura de TraceForge

Visión general de la arquitectura e **índice de ADRs** (Architecture Decision
Records). Cada decisión con alternativas reales se registra como un ADR individual en
[`docs/adr/`](./adr/) con el formato **contexto → decisión → consecuencias**; este
documento da el panorama y enlaza a cada uno, sin duplicar su contenido.

## Panorama (estado F0-T2)

- **Monorepo**: `apps/api` (backend FastAPI, uv), `apps/web` (frontend React+Vite,
  npm), `packages/shared` (cliente TS desde OpenAPI, placeholder). Orquestación con
  **go-task** (`Taskfile.yml`), fuente única de verdad local + CI.
- **Backend**: Python 3.12 + FastAPI, arquitectura por capas
  `router → service → repository` (ver skill `backend-fastapi`). Async de punta a
  punta.
- **Datos**: PostgreSQL 16 + pgvector, acceso async con SQLAlchemy 2 + asyncpg;
  migraciones con Alembic. Redis queda disponible en la infra para fases posteriores
  (aún sin uso en código). **MinIO/almacenamiento: diferido** (deuda conocida; ver
  nota en `compose.yaml` y en `CLAUDE.md`).
- **Infraestructura de desarrollo**: `compose.yaml` levanta db/redis con puertos en
  `127.0.0.1`, volúmenes persistentes y healthchecks (`task up`).
- **Seguridad/multiusuario**: identidad y aislamiento por workspace se resolverán del
  token; principios de IA (procedencia; IA propone / código valida) — ver skills.

## Índice de ADRs

| ADR | Título | Estado |
|---|---|---|
| [0001](./adr/0001-base-de-datos-postgresql-y-driver-async.md) | Base de datos PostgreSQL (con pgvector) y driver async asyncpg | aceptado |
| [0002](./adr/0002-modelo-multiusuario-y-rbac.md) | Modelo multiusuario (multi-tenant) y control de acceso (RBAC) | aceptado |
| [0003](./adr/0003-procedencia-del-contenido-generado-por-ia.md) | Procedencia del contenido generado por IA | aceptado |
| [0004](./adr/0004-ia-propone-codigo-valida.md) | La IA propone, el código determinista valida | aceptado |
| [0005](./adr/0005-politica-de-datos-y-redaccion.md) | Política de datos y redacción de secretos | aceptado |

Documentos relacionados: [`seguridad-datos.md`](./seguridad-datos.md) (resumen operativo de
seguridad/redacción; lo gobierna el ADR-0005).

> Próximos ADRs previstos: capa de "organización" por encima del workspace (si se decide),
> catálogos (CWE/ATT&CK/CVE) y gateway `AIProvider`. **F0-T3b** materializa el modelo base
> (users, workspaces, projects, membresías) y su primera migración a partir del ADR-0002.
