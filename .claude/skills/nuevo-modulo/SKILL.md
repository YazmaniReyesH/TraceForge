---
name: nuevo-modulo
description: >
  Crea el ANDAMIAJE (esqueleto) de un módulo nuevo de TraceForge, en backend
  (Python/FastAPI) y frontend (React/TypeScript), siguiendo las convenciones del proyecto.
  Úsala SIEMPRE que el equipo pida "agregar un módulo", "empezar la fase/tanda X", "crear la
  sección/pantalla de Y" o iniciar cualquier parte nueva (workspaces, proyectos, evidencia,
  hallazgos, documentos, plantillas, tareas de IA, exportación, importación, seguridad).
  Genera estructura y plantillas con TODOs, NO la lógica de negocio: su propósito es avanzar
  ordenado, por partes.
---

# Skill: nuevo-modulo

Genera el esqueleto de un módulo, parejo en backend y frontend, listo para que después se
implemente la lógica con `backend-fastapi` y `frontend-react`. **No implementa reglas de
negocio.**

## Antes de generar nada

1. Ubica el módulo en el **mapa fases/tandas → módulos** del `CLAUDE.md` raíz y confirma su
   nombre en `snake_case` (igual en back y front).
2. Identifica las **entidades del modelo de datos** (ADRs/ficha) que cubre el módulo. Los
   nombres de entidades, campos y estados vienen de ahí; NO se inventan ni renombran.
3. Lee `docs/modulos/<modulo>.md`; si no existe, créalo desde `docs/modulos/_plantilla.md`
   pre-llenando lo que el modelo ya define y marcando `[[POR LLENAR]]` lo que falte.
4. **Presenta un plan corto** (lista de archivos a crear) y espera el visto bueno. No hagas
   git: commits, push y PRs los hace el equipo.

## Qué crea

### Backend — `apps/api/app/modules/<modulo>/`

Archivos con plantillas mínimas y `# TODO` claros:

- `__init__.py`
- `models.py` — una clase SQLAlchemy por entidad, con PK `UUID` (`<entidad>_id`),
  `workspace_id`/`project_id` con FK donde aplique (aislamiento), `created_at`/`updated_at`,
  y `# TODO(equipo)` por cada campo. Estados como `String` + comentario del CHECK pendiente.
- `schemas.py` — `XxxCreate`, `XxxUpdate`, `XxxRead` (Pydantic) con campos como `# TODO`.
  Los campos de origen "Calculado"/"generado por IA validado" SOLO van en `XxxRead`.
- `enums.py` — un `StrEnum` por campo de estado, con los valores exactos del modelo.
- `repository.py` — firmas de `get`, `list`, `create`, `update`, `delete` con `# TODO`,
  todas recibiendo y aplicando el `workspace_id`/`user_id` del contexto.
- `service.py` — clase servicio con métodos espejo + esqueleto de la **máquina de estados**
  (diccionario de transiciones con `# TODO: validar con equipo`). Si el módulo usa IA, deja
  el punto de llamada al puerto `AIProvider` con `# TODO` y nota de redacción/procedencia.
- `router.py` — `APIRouter` con endpoints CRUD declarados, cada uno con
  `Depends(requiere_permiso("<modulo>:<accion>"))`, delegando al servicio. Sin lógica.
- `tests/test_<modulo>.py` con esqueleto.

### Frontend — `apps/web/src/modules/<modulo>/`

- `types.ts` — tipos espejo de los schemas (ideal: generados de OpenAPI).
- `api.ts` — funciones CRUD apuntando a `/api/v1/<modulo>`.
- `hooks.ts` — esqueleto de queries/mutations.
- `components/index.ts` vacío.
- `pages/<Modulo>ListPage.tsx` y, si aplica, `pages/<Modulo>FormPage.tsx` — esqueleto según
  el patrón de pantalla que defina la skill `frontend-react` (pendiente hasta F0-T5). Por
  ahora, dejar el esqueleto con `// TODO: aplicar patrón de pantalla de frontend-react`.

## Después de crear (NO en automático; listarlo como pendiente)

- Registrar el router en `apps/api/app/main.py` y las rutas/menú (con su área RBAC) en el front.
- Crear la migración con la skill `migraciones-postgresql` (la aplica el equipo).
- Completar `docs/modulos/<modulo>.md`, registrar endpoints en `docs/API-CONTRACT.md` y, si
  hay funciones de IA, su entrada en `docs/ai-tasks.md` (skill `documentacion-proyecto`).

## Reglas

- **Cero lógica de negocio**: solo esqueleto y TODOs.
- Nombres de entidades, campos y estados = los del modelo de datos, sin cambios.
- Respetar el espejo back/front y la estructura del `CLAUDE.md` raíz.
- Todo endpoint nace con su dependencia de permiso y con aislamiento por workspace.
- Al terminar, entregar la lista de pasos manuales pendientes y esperar validación.
