# ADR-0017: Análisis de contexto efímero vs. sugerencias persistidas

- **Estado:** aceptado (F1-T4c, 2026-11-06)
- **Supera parcialmente a:** la *superficie de producto* de F1-T4a (ADR-0003/0004 siguen vigentes).

## Contexto

F1-T4a introdujo la primera función de IA de producto como **sugerencias persistidas**
(`description` / `next_step`) con una máquina de estados `pending → accepted/edited` (aprobables,
con auditoría y procedencia). Al llevarlo a la práctica de **documentar en vivo** un pentest, ese
modelo no encaja:

- Lo que el operador necesita mientras trabaja no es una frase para aprobar y guardar, sino una
  **guía de contexto** del momento: qué sigue, cómo va, qué validar, qué cuidar.
- "Aprobar/editar" una sugerencia implica que es contenido estable; pero la evidencia cambia a cada
  paso, así que cualquier sugerencia guardada **queda obsoleta** de inmediato.
- El **orden** del timeline (no la fecha de captura) es la secuencia real de trabajo y debe guiar el
  análisis; las sugerencias F1-T4a no lo modelaban como eje.

Además, llamar al LLM en cada interacción es **caro**; hace falta una estrategia de ahorro que no
complique el dominio (nada de "deltas" ni diffs de evidencia).

## Decisión

1. **Análisis de contexto efímero** (F1-T4c): un endpoint `POST .../sessions/{sid}/analyze` lee la
   **evidencia activa en orden de `position`**, y devuelve una **guía de 4 bloques** con
   `fase_detectada`, **validada** por el código (ADR-0004) antes de entregarse. El resultado es
   **guía viva y desechable**: NO es contenido aprobable (no hay accept/edit). Cada análisis refleja
   el estado de la evidencia en ese instante.

2. **Aparcar (no borrar) el flujo de sugerencias.** Las tablas `ai_suggestions` y
   `ai_redaction_maps` y su código **se conservan** (podrían reutilizarse en la fase de reporte).
   Los endpoints `description`/`next_step` + `accept`/`edit` se marcan **`deprecated=True`** (quedan
   montados y funcionando, tachados en `/docs`) en vez de retirarse del todo: así **no se rompe** lo
   que ya los consume (la UI de F1-T4b, hasta que F1-T4d la sustituya) ni las pruebas existentes, y
   re-activarlos o retirarlos luego es trivial. **No** se genera migración destructiva.

3. **Caché por sesión + hash-guard** (optimización de tokens, sin deltas). Una tabla nueva
   `ai_session_analyses` guarda **una fila por sesión** (la última) con el `state_hash` del estado
   analizable (ítems activos: `id + versión_vigente + posición`, **en orden**, + versión de prompt),
   el resultado estructurado (JSONB), la procedencia (ADR-0003) y el mapeo de redacción **cifrado**
   (ADR-0016). Al pedir análisis: si el `state_hash` coincide con el guardado y no se pasa `force`,
   se **devuelve el guardado sin llamar al LLM** (`from_cache=true`). Solo se llama si el hash cambió
   (editar/reordenar/borrar un ítem lo cambia) o con `force=true`.

4. **Prompt caching** (cuando sí se llama): el **bloque grande de evidencia** se envía como *content
   block* con `cache_control: ephemeral`. Para que sea cacheable byte a byte, la frontera
   anti-inyección del análisis es **determinista derivada del `state_hash`** (en vez del nonce
   aleatorio por llamada de F1-T3) — sigue siendo *inadivinable desde la evidencia* (es un SHA-256 de
   todo el estado ordenado). Beneficio: un refresco `force` del **mismo** estado reutiliza los tokens
   de entrada cacheados dentro de la ventana de caché; **reordenar/editar la evidencia invalida** la
   caché (cambia el hash → cambia la frontera y el bloque).

## Consecuencias

- **A favor:** la IA acompaña el trabajo en vivo sin prometer contenido estable; el orden del
  timeline es la verdad; el hash-guard elimina la mayoría de las llamadas repetidas (y el prompt
  caching abarata las que quedan); el rediseño **no destruye** el trabajo de F1-T4a (reutilizable).
- **En contra / límites:** se mantiene código y dos tablas **sin uso activo** (deuda consciente,
  documentada); la frontera determinista del análisis es un pelín menos opaca que el nonce aleatorio
  (mitigado: deriva de un hash de todo el estado, no de un valor que un ítem pueda fijar); el
  beneficio del prompt caching es acotado (el hash-guard ya evita las llamadas de evidencia idéntica,
  salvo `force`).
- **Procedencia y redacción intactas:** el análisis nace con procedencia (ADR-0003), la evidencia se
  **redacta** antes de salir (ADR-0005) y su mapeo se guarda **cifrado** (ADR-0016) o no se guarda si
  falta la clave (degradación segura). Toda llamada se **registra** en `ai_call_log` (ADR-0015).

## `[[POR LLENAR]]`

- `[[POR LLENAR: retirada o reutilización definitiva de `ai_suggestions`/`ai_redaction_maps` cuando
  se diseñe la fase de **reporte** (que analizará TODAS las sesiones con una plantilla).]]`
- `[[POR LLENAR: retención/purga del caché de análisis y rehidratación efectiva del mapeo cifrado
  (hoy solo se persiste cifrado) — ligado a ADR-0016.]]`
- `[[POR LLENAR: afinar `fase_detectada` y el catálogo de fases con la práctica; posible validación
  contra un catálogo (ATT&CK) en F2, como en ADR-0004.]]`
