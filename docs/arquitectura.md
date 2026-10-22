# Arquitectura de TraceForge

Visión general de la arquitectura e **índice de ADRs** (Architecture Decision
Records). Cada decisión con alternativas reales se registra como un ADR individual en
[`docs/adr/`](./adr/) con el formato **contexto → decisión → consecuencias**; este
documento da el panorama y enlaza a cada uno, sin duplicar su contenido.

## Panorama (estado F0-T3b)

- **Monorepo**: `apps/api` (backend FastAPI, uv), `apps/web` (frontend React+Vite,
  npm), `packages/shared` (cliente TS desde OpenAPI, placeholder). Orquestación con
  **go-task** (`Taskfile.yml`), fuente única de verdad local + CI.
- **Backend**: Python 3.12 + FastAPI, arquitectura por capas
  `router → service → repository` (ver skill `backend-fastapi`). Async de punta a
  punta.
- **Datos**: PostgreSQL 16 + pgvector, acceso async con SQLAlchemy 2 + asyncpg;
  migraciones con Alembic. **Modelo base** (F0-T3b): users, workspaces, projects y las dos
  membresías, con aislamiento por workspace e invariantes de esquema (ver
  [`modulos/modelo-base.md`](./modulos/modelo-base.md), ADR-0002 y ADR-0006).
  Redis queda disponible en la infra para fases posteriores
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
| [0006](./adr/0006-on-delete-y-unicidad-de-owner.md) | Política de borrado (ON DELETE) y unicidad de owner en el modelo base | aceptado |
| [0007](./adr/0007-autenticacion-local-hashing-y-transporte-de-token.md) | Autenticación local: ubicación de credenciales, hashing y transporte de token | aceptado |

Documentos relacionados: [`seguridad-datos.md`](./seguridad-datos.md) (resumen operativo de
seguridad/redacción; lo gobierna el ADR-0005) y la ficha
[`modulos/modelo-base.md`](./modulos/modelo-base.md) (entidades, columnas e invariantes del
modelo base).

> Próximos ADRs previstos: capa de "organización" por encima del workspace (si se decide),
> catálogos (CWE/ATT&CK/CVE) y gateway `AIProvider`. **F0-T3b** materializa el modelo base
> (users, workspaces, projects, membresías) y su primera migración a partir del ADR-0002.
