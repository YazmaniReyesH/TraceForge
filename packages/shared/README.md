# @tf/shared — Cliente TS compartido (placeholder)

Aquí vivirá el **cliente TypeScript generado automáticamente desde el OpenAPI**
del backend (`apps/api`), más los tipos compartidos entre `apps/web` y cualquier
otro consumidor.

## Estado actual (F0-T1)

Vacío a propósito. **No se genera nada todavía**: el backend aún no expone
endpoints de negocio (solo `GET /health`). Generar un cliente ahora sería
mantener código muerto.

## Cuándo se llena

Cuando existan endpoints reales (primeras entidades), se generará el cliente a
partir del esquema OpenAPI que publica FastAPI en `/openapi.json`, por ejemplo con
`openapi-typescript` / `openapi-fetch`. La decisión de herramienta y el comando de
generación se registrarán como ADR en `docs/arquitectura.md` y como target de
`Taskfile.yml` (p. ej. `task gen-client`).

> Regla del proyecto: los tipos del front no se escriben a mano cuando pueden
> derivarse del contrato del backend.
