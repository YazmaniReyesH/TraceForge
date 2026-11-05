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

**F1-T3 no agrega ninguna función de producto de IA todavía** (sugerir paso, generar descripción,
resumen… son **F1-T4**). F1-T3 construye el **andamiaje**: el puerto `AIProvider` (Claude), la
redacción, el ensamblado anti-inyección y la bitácora. Ver la ficha [`modulos/ia.md`](./modulos/ia.md).

## Diagnóstico (no es una función de producto)

| id | Propósito | Prompt (versión) | Salida | Contexto | Proveedor |
|---|---|---|---|---|---|
| `ai.ping` | Verificar el circuito redactar→ensamblar→llamar→registrar con contenido **sintético** | `ping/v1` (instrucción breve + evidencia sintética delimitada) | **Texto libre** (no estructurado): es un diagnóstico, no una función de producto | Solo el contenido **sintético** del ping (no lee evidencia real) | Claude (`TF_ANTHROPIC_MODEL`, por defecto `claude-sonnet-4-5`) |

El ping existe para confirmar que el gateway funciona de extremo a extremo (incluida la redacción y
el ensamblado anti-inyección) contra Claude de verdad; **no** persiste la respuesta del modelo (solo
la devuelve en la respuesta HTTP) y **no** produce contenido para el proyecto. Detalle del ensamblado,
la redacción y la bitácora: [`modulos/ia.md`](./modulos/ia.md) y ADR-0015.

## Funciones de producto (F1-T4+)

`[[POR LLENAR: sugerir-paso, generar-descripción, resumen-de-evidencia… cada una con su id, versión
de prompt, JSON Schema de salida estricto, contexto permitido, capacidades y proveedores — se añaden
al implementarlas en F1-T4.]]`
