# ADR-0005: Política de datos y redacción de secretos

- **Estado:** aceptado
- **Fecha:** 2026-10-21

## Contexto

TraceForge procesa datos altamente sensibles: evidencia de pentests y auditorías que contiene
contraseñas, hashes, claves privadas, tokens, API keys, PII e IPs. El motor de asistencia es
**IA en la nube**, lo que significa que, para muchas funciones, cierto contenido **cruza el
perímetro** hacia un proveedor externo. Debemos permitir ese uso sin filtrar secretos ni datos
de clientes, y hacerlo de forma **auditable** y **gobernada por el cliente**.

Además, la evidencia de un objetivo de pentest es **contenido no confiable**: puede contener
inyección de prompt dirigida al modelo. La política de datos debe partir de esa premisa (el
tratamiento como dato no confiable se detalla en la skill `backend-fastapi` y en la fase del
gateway).

Necesitamos una decisión fundacional sobre **qué sale a la nube, cómo se protege antes de salir y
quién lo decide**, previa a construir cualquier integración de IA.

Alternativas consideradas:

- **Prohibir la nube / solo modelos locales**: hoy no es viable (no se han retomado modelos
  locales) y limitaría demasiado el producto. Queda como limitación conocida, no como opción
  actual.
- **Enviar todo tal cual a la nube**: inaceptable; filtra secretos y datos de clientes.
- **Nube con redacción determinista por defecto + política por proyecto** (la elegida): permite
  el uso de IA en la nube minimizando la exposición, con control por proyecto y auditoría.

## Decisión

**Nube permitida, con redacción activada por defecto y override por proyecto.**

### Redacción antes de salir

- Antes de **cualquier** llamada a un proveedor en la nube, una **capa de redacción
  determinista** reemplaza los secretos por **marcadores estables** (p. ej. un mismo secreto
  produce siempre el mismo marcador dentro de un contexto).
- Se redactan: **contraseñas, hashes, claves privadas, tokens, API keys** siempre; **PII e IPs
  según la clasificación** del proyecto.
- El **mapeo marcador→valor real se guarda cifrado**. Los **valores reales nunca entran en la
  narrativa**: viven en la evidencia cruda (ver ADR-0003). Si hace falta "deshacer" la redacción
  para mostrar a un usuario autorizado, se hace desde ese mapeo cifrado, nunca reenviando el
  valor real al modelo.

### Política por proyecto

- La política de IA es **por proyecto**: **clasificación** del proyecto, **proveedores
  permitidos**, si se **envían imágenes**, y **redacción on/off** (el override). El override se
  ejerce dentro de lo que permita el workspace (ver ADR-0002): un proyecto no puede ser más
  laxo de lo que el workspace autorice.
- La redacción está **activada por defecto**; desactivarla es una decisión explícita y acotada al
  proyecto, con su rastro de auditoría.

### Auditoría y contratación

- **Cada llamada de IA se registra** para auditoría: proveedor, modelo y **qué se envió ya
  redactado** (nunca el contenido sin redactar).
- Para datos de clientes se usa **siempre API bajo contrato** (con sus garantías de no
  entrenamiento/retención), **nunca** suscripciones de consumo tipo producto final de usuario.

## Consecuencias

**A favor:**

- Permite aprovechar IA en la nube **minimizando la exposición** de secretos y datos de clientes.
- **Gobernanza por cliente/proyecto** y **auditoría** completa de lo que sale.
- La redacción determinista con marcadores estables mantiene coherencia en el texto enviado sin
  revelar valores reales.

**En contra / costos asumidos:**

- Hay que construir la **capa de redacción** y el **gateway `AIProvider`** (puerto de dominio con
  implementaciones por proveedor): corresponde a **F1**.
- La redacción determinista nunca es perfecta ante datos arbitrarios; el catálogo de patrones y su
  configuración por clasificación deben mantenerse y revisarse.
  `[[POR LLENAR: catálogo de patrones de redacción y definición de niveles de clasificación —
  se concretará al implementar la redacción (F1)]]`.
- Los **campos de clasificación y política por proyecto** viven en la entidad **`projects`**, y el
  **techo de política** de IA se reserva en la entidad **`workspaces`** (el `lead` solo puede
  igualar o restringir ese techo, nunca relajarlo — ver ADR-0002, "Rol efectivo e invariantes").
  Ambos se materializan en **F0-T3b** (este ADR no fija nombres de columnas).

**Limitación conocida:**

- **No existe un modo totalmente aislado (sin nube)** mientras no se retomen los modelos locales.
  La protección se basa en redacción + política por proyecto + API bajo contrato, no en evitar la
  nube. Esta limitación y el resumen operativo se mantienen en
  [`docs/seguridad-datos.md`](../seguridad-datos.md).

**Referencias cruzadas:**

- Procedencia y conservación de la evidencia cruda: **ADR-0003**.
- Validación determinista de lo sugerido por IA: **ADR-0004**.
- Roles y alcance del override por proyecto dentro del workspace: **ADR-0002**.
