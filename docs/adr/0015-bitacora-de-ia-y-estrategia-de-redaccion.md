# ADR-0015: Bitácora de llamadas de IA y estrategia de redacción

- **Estado:** aceptado
- **Fecha:** 2026-11-05

## Contexto

F1-T3 construye el andamiaje de IA: el gateway `AIProvider` (puerto/adaptador, con Claude detrás),
la **capa de redacción** de secretos, el **ensamblado de prompt** con la evidencia como dato no
confiable y la **bitácora de llamadas**. Es la primera vez que el proyecto hace llamadas externas
reales (de pago) hacia un proveedor en la nube. El ADR-0005 ya decidió *que* se redacta y *que* cada
llamada se audita; aquí se concretan dos decisiones con alternativas reales:

1. **Qué guarda exactamente la bitácora** sin reintroducir secretos.
2. **Cómo se redacta** de forma determinista sin romper la estructura que el modelo necesita.

## Decisión

### 1. Qué guarda la bitácora (`ai_call_log`)

Se registra **una fila por llamada**: `provider`, `model`, `status`
(`ok|error|not_configured`), `input_tokens`/`output_tokens` (si el SDK los da), `created_by`,
`workspace_id`/`project_id` (aislamiento), `created_at`, y sobre lo enviado:

- **`redacted_prompt`**: el prompt de usuario **ya redactado** (exactamente lo que cruzó el
  perímetro, nunca más).
- **`redacted_prompt_sha256`**: SHA-256 del prompt redactado (integridad / deduplicación).
- **`redaction_count`**: cuántos secretos se enmascararon (métrica, sin revelar valores).
- **`error_code`**: código de error de dominio estable (nunca un mensaje con secretos). `None` si ok.

**Nunca** se guarda: el contenido **sin redactar**, el **mapeo marcador→valor**, ni la **API key**.

Alternativas consideradas para "qué se envió":

- **A. Guardar solo un hash de lo enviado.** No reintroduce nada, pero deja la auditoría ciega: ante
  una duda ("¿qué le mandamos al proveedor?") no hay respuesta, solo un hash opaco.
- **B. Guardar el prompt redactado + su hash (elegida).** La auditoría puede ver *exactamente* lo
  que salió. Clave: ese texto **ya cruzó** hacia el proveedor y vive en **el mismo perímetro** que la
  evidencia de la que salió; guardarlo en nuestra propia BD **no añade exposición nueva**. El hash da
  integridad. El invariante real ("jamás el valor crudo ni el mapeo ni la key") se respeta igual.
- **C. Guardar el prompt crudo.** Inaceptable: reintroduce secretos en la BD (viola ADR-0005).

No se guarda la **respuesta** del modelo en la bitácora de T3: el requisito de auditoría del
ADR-0005 es "qué se **envió** ya redactado"; la respuesta puede contener contenido inyectado por el
objetivo y su persistencia se evaluará cuando exista una función de producto (F1-T4). El ping sí la
**devuelve** en la respuesta HTTP (para verificar el circuito), pero no la persiste.

`status = not_configured` también se registra (hubo un intento), con `redacted_prompt` pero sin
tokens: deja rastro de que alguien pidió IA sin que esté configurada.

FKs: `workspace_id`/`project_id` con `ON DELETE CASCADE` (coherente con el borrado del contenido del
project, ADR-0006); `created_by` con `RESTRICT`. `status` es `VARCHAR(20)` + CHECK nombrado (mismo
patrón que `kind`/roles).

### 2. Estrategia de redacción

Redacción **determinista por patrones** (NO IA), con **marcadores estables** (mismo secreto → mismo
marcador dentro de un texto: `[REDACTED_<TIPO>_<n>]`). Devuelve el texto redactado, el mapa
marcador→valor **en memoria** (no se persiste en T3; el mapeo cifrado es F1-T4) y el conteo.

- **Preserva la estructura.** En una asignación se enmascara **solo el valor** y se conserva la clave
  (`password=[REDACTED_PASSWORD_1]`); `Bearer` y el encabezado PEM se conservan como pista de forma.
  Así el modelo sigue "entendiendo" que había una contraseña/clave sin ver su valor. Equilibrio
  explícito: redactar de más rompería la estructura que el modelo necesita analizar.
- **Qué se redacta (alto riesgo, siempre):** claves privadas PEM, JWT, claves `sk-`/`pk-`/`rk-`,
  `AKIA…` (AWS), token tras `Bearer`, asignaciones `api_key/secret/token/…=` y `password=`, y
  hashes hex (sha256/sha1/md5). **PII e IPs quedan fuera por defecto** (dependen de la clasificación
  del proyecto, aún reservada en `projects.ai_policy`).
- **Orden específico → genérico** y guarda anti-doble-redacción (no re-redacta un marcador ya puesto).

**Relación con el realce semántico del frontend (F1-T2):** comparten la *forma* del patrón de hash,
pero **no se acoplan**. Son cosas opuestas (la redacción **oculta** en el backend antes de salir a la
nube; el realce **colorea** en el navegador) y viven en lenguajes distintos (Python vs TypeScript);
acoplarlas obligaría a compartir un origen entre dos capas con metas contrarias. Duplicar un patrón
pequeño es más seguro que ese acoplamiento. Alternativa descartada: una librería compartida de
patrones entre back y front.

### 3. Puerto, ensamblado y ping (contexto de la decisión)

- **Puerto `AIProvider`** (dominio, no SDK): `complete(prompt, max_tokens) -> AICompletion`, más
  `name`/`model`/`is_configured`. Claude detrás (SDK `anthropic`, import perezoso). OpenAI/Gemini
  serían otras implementaciones (F4), como `AuthProvider` (ADR-0007). "IA no configurada" (sin API
  key) degrada con claridad, no rompe.
- **Ensamblado anti-inyección:** la evidencia (ya redactada) se envuelve en una **frontera única con
  nonce** por llamada y el `system` instruye tratar lo de dentro como datos, nunca instrucciones.
- **Ping** (`POST …/ai/ping`): toma contenido sintético (con secreto falso + inyección falsa), lo
  pasa por redacción → ensamblado → proveedor → bitácora, y devuelve el resultado. Siempre **200**
  con un `status` (reporta el circuito; no es el circuito).

## Consecuencias

**A favor:** auditoría con valor real (se ve lo que se envió, ya redactado) sin exposición nueva ni
secretos crudos; redacción determinista, reproducible y que no rompe la estructura; gateway
desacoplado del SDK (cambiar/añadir proveedor no toca servicio ni endpoints); defensa anti-inyección
de base para cuando lleguen las funciones de producto.

**En contra / costos:** la redacción determinista **nunca es perfecta** ante datos arbitrarios (hay
que mantener y ampliar el catálogo de patrones); guardar el prompt redactado ocupa más que un hash;
la bitácora crece con cada llamada (su retención/purga queda pendiente, como la de evidencia).

`[[POR LLENAR: catálogo de patrones de redacción ampliado y redacción de PII/IPs por clasificación
(política de IA por proyecto); persistencia cifrada del mapeo marcador→valor (F1-T4); retención/purga
de la bitácora.]]`

## Alcance

Backend de F1-T3. No hay función de producto de IA todavía (F1-T4) ni UI ni frontend. No cambia el
esquema salvo la nueva tabla `ai_call_log` (migración `b7d9e1c4a2f5`, la aplica el equipo).
