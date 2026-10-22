# ADR-0006: Política de borrado (ON DELETE) y unicidad de owner en el modelo base

- **Estado:** aceptado
- **Fecha:** 2026-10-21

## Contexto

Al materializar el modelo base (F0-T3b: users, workspaces, projects y las dos membresías)
hay que decidir el comportamiento de las llaves foráneas ante borrados y cómo garantizar, a
nivel de esquema, el invariante "un solo owner por workspace" del ADR-0002. Son decisiones con
alternativas reales (CASCADE vs RESTRICT; constraint vs índice parcial) que conviene registrar.

La skill `migraciones-postgresql` fija el criterio general: **preferir `RESTRICT`/`NO ACTION`
salvo que la cascada sea parte del diseño** (p. ej. borrar un contenedor lógico y todo lo que
cuelga de él). El ADR-0002 define el workspace como frontera de aislamiento y el proyecto como
contenedor de su contenido.

## Decisión

### ON DELETE de las FKs

- **`projects.workspace_id → workspaces`: `ON DELETE CASCADE`.** Borrar un workspace es borrar el
  inquilino completo; sus proyectos (y, por diseño, lo que cuelgue de ellos) desaparecen con él.
- **`workspace_memberships.workspace_id → workspaces`: `ON DELETE CASCADE`.** Las membresías de un
  workspace borrado no tienen sentido por sí solas.
- **`project_memberships.project_id → projects`: `ON DELETE CASCADE`.** Igual para el proyecto:
  borrarlo arrastra sus membresías. (Y como borrar un workspace cae en cascada a sus proyectos,
  también se limpian las membresías de esos proyectos.)
- **`*_memberships.user_id → users`: `ON DELETE RESTRICT`.** **No** se puede borrar un `user` que
  todavía tenga membresías. El borrado de un usuario debe ser un flujo **explícito** del servicio
  (revocar membresías, resolver la titularidad de los workspaces que posea y, en su caso,
  anonimizar), no un efecto colateral silencioso de un `DELETE`. Esto protege contra dejar un
  workspace sin owner o perder rastros de forma accidental.

### Unicidad de owner

- "**Un solo owner por workspace**" se garantiza con un **índice único PARCIAL**:
  `CREATE UNIQUE INDEX uq_workspace_memberships_single_owner ON workspace_memberships (workspace_id) WHERE role = 'owner';`
  Es la forma natural en PostgreSQL de imponer "como máximo una fila que cumpla una condición" por
  grupo, sin tablas ni triggers extra.

## Consecuencias

**A favor:**

- La cascada por workspace/proyecto hace el borrado de un inquilino o un proyecto atómico y
  limpio, sin huérfanos.
- `RESTRICT` sobre `user_id` obliga a un borrado de usuario **deliberado y seguro**, alineado con
  un producto donde la baja de un usuario tiene implicaciones (titularidad, auditoría, privacidad).
- El índice parcial impone el "máximo un owner" en la base, de forma barata e inmediata.

**En contra / costos asumidos:**

- El índice parcial cubre el **"como máximo uno"**, pero **no** el **"al menos uno"**: que un
  workspace no se quede **sin** owner es un **invariante de servicio** (F0-T4), igual que la
  transferencia atómica de propiedad y la regla `guest` = solo `viewer` (ver ADR-0002).
- `RESTRICT` en `user_id` implica que el servicio de borrado de usuario (F0-T4+) deberá limpiar
  membresías y resolver titularidades antes de poder borrar; se asume ese trabajo a cambio de
  seguridad.

**Alcance:**

- Este ADR documenta decisiones ya **implementadas en la primera migración** de F0-T3b. No
  introduce cambios de esquema adicionales.
