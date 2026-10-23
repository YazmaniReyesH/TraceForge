# ADR-0009: Convención de errores de la API (envelope {code, message})

- **Estado:** aceptado
- **Fecha:** 2026-10-23

## Contexto

El backend expone errores de dominio (credenciales inválidas, único owner, guest=viewer, no
encontrado, etc.). Hasta F0-T4b cada router los traducía a `HTTPException` con un `detail` de
texto en español, y FastAPI devolvía formatos distintos (`{"detail": "..."}` para HTTPException,
lista para validación). El frontend (F0-T5a) necesita **mapear el error a un mensaje i18n de
forma estable**, sin depender del texto del backend ni del status a secas.

## Decisión

Todos los errores de la API se devuelven con un **envelope uniforme**:

```json
{ "code": "invalid_credentials", "message": "Credenciales inválidas" }
```

- El **`code`** es estable y es lo que el frontend mapea a i18n; el `message` es un texto de
  respaldo en español (para logs/clientes sin i18n), nunca la fuente de verdad de la UI.
- Los **errores de dominio** heredan de `DomainError` (`app/core/errors.py`) y declaran su
  `code` y su `status_code`. Un **manejador central** los traduce al envelope. También se
  normalizan las `HTTPException` de Starlette y los errores de validación de entrada.
- **Mapeo de status:** validación de entrada → **422** (`validation_error`); conflicto de
  negocio → **409**; permiso → **403** (`forbidden`); no encontrado / sin acceso → **404**
  (`not_found`); no autenticado → **401** (`unauthenticated`).
- **Reclasificación:** `guest = viewer` pasa de 422 a **409** (`guest_must_be_viewer`), por ser
  un conflicto de regla de negocio, no un error de forma del input.
- Códigos iniciales: `email_already_registered`, `invalid_credentials`, `sole_owner`,
  `cannot_assign_owner`, `already_owner`, `member_exists`, `not_a_member`, `not_workspace_member`,
  `guest_must_be_viewer`, `user_has_memberships`, `user_not_found`, `csrf_failed`, `forbidden`,
  `not_found`, `unauthenticated`, `validation_error`.
- Los routers **dejan propagar** los errores de dominio al manejador central (no los capturan),
  lo que adelgaza los routers.

## Consecuencias

**A favor:** una sola forma de error; el frontend mapea por `code` a i18n sin suposiciones
frágiles; routers más delgados; códigos estables y auditables.

**En contra / costos:** hay que mantener la tabla de `code`↔status en los errores de dominio y
el catálogo i18n en el frontend sincronizados. Un `code` nuevo sin su clave i18n cae al mensaje
genérico (`errors.unknown`).

**Nota de seguridad:** `email_already_registered` (409 en el registro) sigue permitiendo
enumeración de usuarios por `code`/status; es una **deuda conocida** (ADR-0007) que se cierra con
verificación por email.

**Referencias:** el frontend consume este contrato en `src/shared/api` (ADR-0008 para 401/403/404).
