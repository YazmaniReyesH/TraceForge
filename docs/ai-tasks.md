# AI Tasks — registro de funciones de IA de TraceForge

Registro vivo de las **funciones de IA** del producto: cada una con su `id`, propósito, **versión de
prompt**, **JSON Schema** de salida, contexto permitido (qué lee), capacidades requeridas (visión,
salida estructurada, contexto) y proveedor(es) permitido(s). Una función de IA **no está terminada**
sin su entrada aquí (skill `documentacion-proyecto`). Esto hace que agregar una función sea *agregar
una entrada*, no inventar un flujo.

Reglas transversales (ADR-0003/0004/0005):

- Toda salida de IA es una **sugerencia con procedencia** y nace **pendiente** (ADR-0003).
- La **IA propone, el código valida/calcula** (ADR-0004): nada con semántica dura (CVSS, CWE, CVE,
  ATT&CK) se persiste/mostrar sin validación determinista.
- **Antes de llamar** a la nube, la evidencia pasa por **redacción** (ADR-0005) y se **ensambla como
  dato no confiable** (anti-inyección). Cada llamada se **registra** en `ai_call_log`.

## Estado

**F1-T4a agrega las dos primeras funciones de producto de IA** (`description` y `next_step`), sobre el
andamiaje de F1-T3 (puerto `AIProvider`/Claude, redacción, ensamblado anti-inyección, bitácora). Nacen
`pending` con procedencia (ADR-0003) y usan **salida estructurada validada** (ADR-0004). La evidencia
real pasa por **redacción** y su mapeo se guarda **cifrado** (ADR-0016). Ver [`modulos/ia.md`](./modulos/ia.md).

## Diagnóstico (no es una función de producto)

| id | Propósito | Prompt (versión) | Salida | Contexto | Proveedor |
|---|---|---|---|---|---|
| `ai.ping` | Verificar el circuito redactar→ensamblar→llamar→registrar con contenido **sintético** | `ping/v1` (instrucción breve + evidencia sintética delimitada) | **Texto libre** (no estructurado): es un diagnóstico, no una función de producto | Solo el contenido **sintético** del ping (no lee evidencia real) | Claude (`TF_ANTHROPIC_MODEL`, por defecto `claude-sonnet-4-5`) |

El ping existe para confirmar que el gateway funciona de extremo a extremo (incluida la redacción y
el ensamblado anti-inyección) contra Claude de verdad; **no** persiste la respuesta del modelo (solo
la devuelve en la respuesta HTTP) y **no** produce contenido para el proyecto. Detalle del ensamblado,
la redacción y la bitácora: [`modulos/ia.md`](./modulos/ia.md) y ADR-0015.

## Funciones de producto (F1-T4a)

Ambas comparten el patrón **sugerir → validar → persistir** (ADR-0004): la IA devuelve JSON; el
servicio valida la forma contra el schema antes de persistir (si no cumple → `ai_invalid_output`, no se
persiste). Contexto permitido: **solo la evidencia de la sesión indicada, ya redactada** (ADR-0005);
no leen otras sesiones ni proyectos. Sin herramientas habilitadas para el modelo. Nacen `pending`
(ADR-0003) con procedencia (proveedor, modelo resuelto, versión de prompt, `ai_call_log_id`,
`input_refs`). Proveedor: Claude (`ai_policy.model` del proyecto si está; si no, `TF_ANTHROPIC_MODEL`).

| id | Propósito | Prompt (versión) | JSON Schema de salida | Contexto |
|---|---|---|---|---|
| `description` | Describir la evidencia de la sesión (función principal) | `description/v1` | `{"description": string (≥1)}` | Evidencia de la sesión (redactada) |
| `next_step` | Sugerir un siguiente paso y su justificación | `next_step/v1` | `{"next_step": string (≥1), "rationale": string (≥1)}` | Evidencia de la sesión (redactada) |

- **Salida estructurada estricta:** se exige un objeto JSON con exactamente los campos del schema
  (campos extra se ignoran; faltantes o vacíos → rechazo). El texto canónico de la sugerencia es
  `description` / `next_step`; el resto del payload validado se conserva en `suggested_payload`.
- **Capacidades requeridas:** salida estructurada (JSON) + contexto. **No** visión (no se envían
  imágenes en esta tanda). **No** validación contra catálogos (no hay CWE/CVE/ATT&CK aquí; eso es F2,
  pero el patrón de validación determinista ya queda listo).
- **Transiciones** (ADR-0003): `pending → accepted` | `pending|edited → edited`; `accepted` terminal.
  La edición humana se guarda aparte y conserva el contenido sugerido original + el rastro de IA.

`[[POR LLENAR: resumen-de-evidencia, CVSS, CWE/CVE/ATT&CK, traducción… (F1-T4b+/F2), cada una con su
id, versión de prompt, JSON Schema, contexto, capacidades y validación contra catálogo.]]`
