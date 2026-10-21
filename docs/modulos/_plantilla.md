# Ficha de módulo: <nombre_del_modulo>

> Copia este archivo a `docs/modulos/<modulo>.md` (nombre en `snake_case`, igual
> en backend y frontend) al iniciar un módulo. Pre-llena lo que el modelo de datos
> ya define y marca `[[POR LLENAR: ...]]` lo que falte. Documentación **viva**: se
> actualiza en el mismo PR que el código.

- **Fase / tanda:** <p. ej. F1-T2>
- **Estado del módulo:** andamiaje | en desarrollo | terminado
- **Responsable:** <quién>
- **Última actualización:** AAAA-MM-DD

## Propósito

Qué resuelve este módulo y para qué rol(es) existe. Una o dos frases.

## Entidades y estados

Para cada entidad del modelo de datos que cubre el módulo:

- **<Entidad>** (`<entidad>_id`): descripción breve.
  - Campos clave: `campo` — qué es, origen (ingresado / calculado / IA validado).
  - Estados (`StrEnum`): `valor1`, `valor2`, … con su CHECK constraint nombrado.
  - Transiciones válidas: `valor1 → valor2` (… ). Inválida → 409.
  - Aislamiento: `workspace_id` / `project_id` por los que filtra el repository.

## Pantallas (frontend)

- **<Pantalla>**: qué muestra, qué rol la usa, acciones disponibles.

## Endpoints

Resumen; el contrato completo (permisos, ejemplos, errores) va en
`docs/API-CONTRACT.md`.

| Método | Ruta | Permiso | Descripción |
|---|---|---|---|
| GET | /api/v1/<modulo> | `<modulo>:listar` | … |

## Funciones de IA (si aplica)

Enlazar cada una a su entrada en `docs/ai-tasks.md` (id, prompt versionado, schema,
procedencia, redacción). Si no usa IA: "N/A".

## Decisiones y pendientes

- Decisiones tomadas (enlazar al ADR en `docs/adr/` si hubo una).
- `[[POR LLENAR: ...]]` lo que falte por resolver.
- Lo aprendido al implementar.
