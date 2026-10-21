---
name: migraciones-postgresql
description: >
  Cómo crear y revisar migraciones de base de datos de TraceForge con Alembic sobre
  PostgreSQL. Úsala SIEMPRE que se vaya a cambiar el esquema: crear o alterar tablas,
  columnas, índices, llaves foráneas, CHECK constraints de estados, columnas JSONB o
  pgvector, o al implementar entidades del modelo de datos. El esquema NUNCA se cambia a
  mano en la base: siempre por migración. IMPORTANTE: Claude Code NO tiene acceso directo a
  la base de datos; genera y revisa el archivo de migración, pero NO la aplica — el equipo
  revisa el SQL y ejecuta la migración manualmente.
---

# Skill: migraciones-postgresql

Toda modificación del esquema pasa por Alembic contra PostgreSQL. Nada de cambios manuales
en la base con un cliente SQL.

## Regla de oro sobre quién aplica

- **Claude Code genera** la migración y la deja lista y comentada.
- **El equipo revisa el SQL y la aplica** (`alembic upgrade head`). Claude Code no corre
  migraciones ni asume que puede: no tiene conexión a la base.
- En el PR va el archivo de migración + la ficha del módulo actualizada.

## Flujo

1. Ajustar/crear el modelo SQLAlchemy en `apps/api/app/modules/<modulo>/models.py`
   siguiendo el modelo de datos del proyecto (nombres, tipos y restricciones).
2. Generar la migración:
   ```bash
   alembic revision --autogenerate -m "crear tabla hallazgo"
   ```
3. **Revisar SIEMPRE** el archivo generado en `apps/api/migrations/versions/`: la
   autogeneración no detecta bien renombres ni algunos ALTER. Confirmar tipos, nulabilidad,
   FKs, índices, CHECKs, JSONB/vector y que el `downgrade` revierta correctamente.
4. El equipo aplica en desarrollo: `alembic upgrade head`.
5. Verificar que la app levanta y las pruebas pasan.
6. Antes de dar la migración por buena: `alembic upgrade head` sobre una base vacía y un
   viaje redondo `downgrade` → `upgrade` sobre una copia con datos.

## Convenciones de esquema (PostgreSQL)

- **PK**: `UUID` con default `gen_random_uuid()` (extensión `pgcrypto`) o generación en app;
  ser consistentes. Nombre `<entidad>_id`.
- **Textos**: `Text` o `String(n)` según la longitud. **Dinero/decimales**: `Numeric(p,s)`,
  nunca `float`/`double`.
- **Fechas**: `timestamptz`. **Booleanos**: `Boolean`.
- **Estados (enum del dominio)**: columna `String` + **CHECK constraint nombrado** con los
  valores exactos, p.ej.:
  ```sql
  CONSTRAINT ck_hallazgo_estado CHECK (estado IN
    ('abierto','remediado','retesteado','cerrado'))
  ```
  Preferimos `VARCHAR + CHECK` sobre el `ENUM` nativo de Postgres: agregar un valor a un enum
  nativo obliga a `ALTER TYPE` y complica los downgrades; con CHECK es una migración simple.
  Dar nombre explícito a cada constraint.
- **JSONB**: para documentos de bloques y salidas de IA estructuradas (`JSONB`, no `JSON`).
  Índice `GIN` si se va a consultar por contenido.
- **pgvector**: columnas `vector(n)` para embeddings; crear la extensión `vector` en una
  migración temprana e índice `ivfflat`/`hnsw` cuando el volumen lo justifique.
- **FKs explícitas** con ON DELETE pensado (evitar cascadas accidentales; preferir
  `RESTRICT`/`NO ACTION` salvo acuerdo, p.ej. borrar un proyecto sí cae en cascada a su
  evidencia por diseño — documentarlo).
- **Aislamiento multiusuario**: toda tabla de datos de usuario lleva su `workspace_id`
  (y/o `project_id`) con FK e índice; es la columna por la que el repository filtra siempre.
- **Índices**: en FKs y en columnas de búsqueda/filtrado frecuentes (estados, fechas,
  `workspace_id`, `project_id`).
- **Timestamps**: `created_at NOT NULL` (+ `updated_at`, `created_by` donde aplique).
- **Relación N:M**: tabla puente con su propia PK (p.ej. hallazgo ↔ técnica ATT&CK).

## Datos iniciales (seeds)

- Catálogos con valores predefinidos (CWE, MITRE ATT&CK, CVE en caché, roles) → migraciones
  de datos separadas y claramente nombradas, o un mecanismo de seed aparte.
  Estrategia exacta: `[[POR LLENAR: definir en el ADR de catálogos]]`.
- Nunca incluir secretos ni datos personales reales en migraciones.

## Reglas

- Una migración por cambio lógico, mensaje descriptivo en español.
- La migración y la ficha del módulo (`docs/modulos/`) se actualizan en el mismo PR.
- Claude Code deja la migración lista y señala explícitamente: "pendiente de aplicar por el
  equipo; revisar el SQL antes de ejecutar".
