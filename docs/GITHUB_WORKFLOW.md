# Flujo de trabajo Git / Pull Requests — TraceForge

Cómo lleva el equipo los cambios a `main`, para no tener que recordarlo de memoria.
Se trabaja en **tandas** (fase-tanda, p. ej. F0-T2); **cada tanda va por rama + PR**.

> **Quién hace qué:** **Claude Code NO ejecuta git** (ni `add`/`commit`/`push` ni abre
> PRs) y **NO aplica migraciones**. Genera el código y las migraciones; **el equipo**
> revisa, commitea, abre el PR y aplica las migraciones (`alembic upgrade head` tras
> revisar el SQL). Ver skill `migraciones-postgresql`.

## (a) Nota de arranque

El **primer commit** del repositorio (F0-T1) estableció `main` directamente y por eso
**no llevó PR**. **De F0-T2 en adelante, toda tanda va por rama + PR** contra `main`.

## (b) Crear la rama de la tanda (desde `main` actualizado)

```bash
git switch main
git pull
git switch -c feat/<fase-tanda>-<slug>
```

Convención de nombre: `feat/<fase-tanda>-<slug>`.
Ejemplo: `feat/f0-t2-infra-postgres`.

## (c) Revisar y commitear (commits pequeños y descriptivos, en español)

```bash
git status
git diff
git add -A
git commit -m "F0-T2: levantar infra en contenedores y conectar Postgres"
```

- Mensaje **en español**, con **prefijo de tanda** (`F0-T2: ...`).
- Commits pequeños y enfocados. **El código y su documentación viajan en el mismo
  commit/PR** (regla del proyecto).

## (d) Publicar la rama

```bash
git push -u origin feat/<fase-tanda>-<slug>
```

## (e) Abrir el Pull Request y mergear

1. En GitHub, abre un PR: **base `main` ← compare `feat/<fase-tanda>-<slug>`**.
2. Descripción clara en español: qué incluye la tanda y cómo se validó. Incluye la
   documentación de `docs/` actualizada.
3. **Espera a que CI esté en verde** (jobs de backend y frontend).
4. **Squash and merge** (un commit limpio por tanda en `main`).
5. **Borra la rama remota** (GitHub ofrece el botón al mergear).

## (f) Sincronizar local

```bash
git switch main
git pull
git branch -d feat/<fase-tanda>-<slug>
```

## (g) Recordatorios

- **Claude Code no ejecuta git**: todo lo de arriba lo hace el equipo.
- **Migraciones**: Claude Code deja el archivo de migración listo y comentado; el
  equipo **revisa el SQL** y la **aplica** (`task db-upgrade` / `alembic upgrade head`).
  Nunca se cambia el esquema a mano en la base.
- **Secretos**: el `.env` real no se commitea; solo `.env.example` con valores de
  desarrollo.
- Una tanda **no está terminada** si su documentación viva no está actualizada en el
  mismo PR (ver skill `documentacion-proyecto` y `revision-modulo`).
