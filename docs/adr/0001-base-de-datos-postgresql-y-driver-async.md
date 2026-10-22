# ADR-0001: Base de datos PostgreSQL (con pgvector) y driver async asyncpg

- **Estado:** aceptado
- **Fecha:** 2026-10-21

## Contexto

TraceForge es una plataforma de documentación técnica para TI/Ciberseguridad,
multiusuario desde el inicio, con aislamiento por workspace/proyecto y funciones de
IA en la nube. Del modelo de datos y de los principios del proyecto se desprenden
varias necesidades concretas para la capa de persistencia:

- **Integridad relacional fuerte**: usuarios, workspaces, proyectos, membresías,
  evidencia, hallazgos y documentos tienen relaciones y restricciones (FKs, CHECKs de
  estados) que deben garantizarse en la base, no solo en la app.
- **Documentos de bloques y salidas de IA estructuradas** que conviene guardar como
  **JSONB** (consultable e indexable con GIN).
- **Búsqueda semántica / detección de duplicados** sobre embeddings en fases
  posteriores, lo que requiere un tipo vectorial nativo.
- **Backend async**: FastAPI es async; mezclar E/S de base sync bloquearía el event
  loop. Necesitamos acceso a base asíncrono y consistente en todo el backend.
- Queremos una sola base relacional, madura, open source y reproducible en local vía
  contenedores, sin acoplarnos a un proveedor cloud concreto.

Alternativas consideradas:

- **Motor de base**: PostgreSQL vs. MySQL/MariaDB vs. SQLite. SQLite no sirve para
  multiusuario concurrente ni para los tipos que necesitamos; MySQL tiene JSON y
  soporte vectorial más débiles y un ecosistema de extensiones menor.
- **Vector**: extensión **pgvector** dentro de Postgres vs. una base vectorial
  dedicada (Qdrant, Milvus, Weaviate). Una base aparte añade un sistema más que
  operar, sincronizar y respaldar, para un volumen que al inicio es modesto.
- **Driver async**: **asyncpg** vs. **psycopg3** (async). Ambos son válidos con
  SQLAlchemy 2; asyncpg es el más rápido y probado para cargas async puras y no
  necesitamos (todavía) las características extra de psycopg3.

## Decisión

Usaremos **PostgreSQL 16 con la extensión pgvector** como única base de datos
relacional del proyecto, en contenedor para desarrollo (imagen
`pgvector/pgvector:pg16`, con los puertos ligados a `127.0.0.1`).

El backend accederá a la base con **SQLAlchemy 2 en modo asíncrono usando el driver
`asyncpg`** (`postgresql+asyncpg://...`). El engine, el `async_sessionmaker`, la
`Base` declarativa y la dependencia `get_session` viven centralizados en
`apps/api/app/core/db.py`, y **todo el backend es async de forma consistente** (sin
sesiones sync mezcladas).

Las migraciones de esquema se gestionan con **Alembic en modo async** apuntando a
`Base.metadata` y leyendo `TF_DATABASE_URL`.

## Consecuencias

**A favor:**

- Una sola tecnología de datos cubre relacional, JSONB y vectorial: menos piezas que
  operar, un solo respaldo, transacciones que abarcan todo.
- asyncpg no bloquea el event loop de FastAPI; buen rendimiento bajo concurrencia.
- Reproducible en local con `task up`; la misma imagen (pgvector/pgvector:pg16) corre
  en CI como service container para las pruebas de readiness.
- pgvector queda disponible desde el día uno para la búsqueda semántica futura.

**En contra / costos asumidos:**

- asyncpg usa su propio sistema de *prepared statements*, lo que puede requerir
  cuidados con PgBouncer en *transaction pooling* (configurar `statement_cache_size`
  o usar `NullPool`) cuando llegue el despliegue. `[[POR LLENAR: definir en el ADR de
  despliegue/pooling]]`.
- Todo el equipo debe escribir código de base **async** (más disciplina que el estilo
  sync tradicional).
- pgvector a gran escala puede necesitar índices `ivfflat`/`hnsw` y tuning; se
  abordará cuando el volumen lo justifique, no ahora.
- Preferimos `VARCHAR + CHECK` sobre `ENUM` nativo de Postgres para los estados del
  dominio (ver skill `migraciones-postgresql`), para simplificar la evolución del
  esquema.
