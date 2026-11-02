# ADR-0011: Edición y borrado protegido de workspace

- **Estado:** aceptado
- **Fecha:** 2026-10-23

## Contexto

Las pantallas de dominio (F0-T5b) necesitan **editar** y **eliminar** workspaces, pero el backend
solo tenía crear/listar/detalle + miembros/transferencia. Faltaban `PATCH` y `DELETE`.

Eliminar un workspace es delicado: la FK de `projects`/membresías es `ON DELETE CASCADE`
(ADR-0006), así que un `DELETE` directo borraría en cascada **todo** el contenido del workspace.
Para la Fase 0 no queremos exponer un borrado masivo irreversible desde la UI.

## Decisión

- **`PATCH /api/v1/workspaces/{id}`** — edita el nombre. Permiso **`workspaces:update`**
  (owner/admin). Directo.
- **`DELETE /api/v1/workspaces/{id}`** — permiso **`workspaces:delete`** (**solo owner**), y
  **protegido a nivel de servicio**: solo se permite si el workspace **no tiene projects** y su
  **único miembro es el owner** que lo borra. Si no se cumple → error de dominio
  **`workspace_not_empty`** (409), **sin** borrado en cascada. Así el `DELETE` desde la UI nunca
  dispara una cascada destructiva: para borrar hay que vaciar el workspace primero (quitar
  miembros y projects).
- Ambos respetan las capas (router → service → repository) y el envelope de errores (ADR-0009);
  sin migración (lógica sobre tablas existentes; la cascada de ADR-0006 se conserva como red de
  seguridad del esquema, pero el servicio no la provoca).

## Consecuencias

**A favor:** borrado seguro y predecible; owner-only; mensajes por `code`; sin tocar el esquema.

**En contra / costos:** no se puede borrar un workspace "con contenido" en un paso; el usuario
debe vaciarlo antes. El **borrado con contenido** (cascada controlada, quizá con confirmación
fuerte o soft-delete) queda como función futura más protegida.
`[[POR LLENAR: borrado de workspace con contenido / soft-delete]]`.

## Alcance

Backend de F0-T5b (checkpoint 1). La UI que los consume es el checkpoint 2 de F0-T5b.
