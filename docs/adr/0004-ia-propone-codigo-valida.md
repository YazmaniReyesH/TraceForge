# ADR-0004: La IA propone, el código determinista valida

- **Estado:** aceptado
- **Fecha:** 2026-10-21

## Contexto

Varias funciones de IA de TraceForge producirán **datos estructurados con significado técnico
preciso**: un vector CVSS, un identificador CWE, un CVE, una técnica MITRE ATT&CK, un puntaje.
Estos valores tienen reglas y catálogos oficiales. Un modelo de lenguaje puede **inventar** un
identificador plausible pero inexistente (p. ej. un "CVE" que no existe o un CWE mal escrito), o
**calcular mal** un score. Mostrar un dato así en un reporte de seguridad sería un error grave:
compromete la credibilidad y puede inducir decisiones equivocadas.

Necesitamos una regla fundacional que separe claramente **qué aporta la IA** (propuesta,
lenguaje, borrador) de **qué garantiza el sistema** (corrección, existencia, cálculo), para que
ningún valor con semántica dura dependa de la "buena fe" del modelo.

Alternativas consideradas:

- **Confiar en la salida del modelo tal cual** (incluidos scores e identificadores): inaceptable
  por el riesgo de IDs inventados y cálculos erróneos.
- **Pedir al modelo que "verifique" lo suyo** con otra llamada: no es determinista ni auditable;
  sigue sin garantía de existencia/corrección.
- **IA propone → código valida/calcula** (la elegida): la IA sugiere; una capa determinista
  calcula lo calculable y valida lo verificable contra catálogos locales antes de aceptar o
  mostrar nada.

## Decisión

**La IA propone y el código determinista calcula o valida.** Ningún valor con semántica dura se
persiste ni se muestra solo porque la IA lo haya dicho.

Patrón obligatorio para las funciones de IA de clasificación: **sugerir → validar → persistir**.

- **Sugerir**: el modelo devuelve una propuesta con **salida estructurada** (JSON Schema
  estricto; ver skill `backend-fastapi`).
- **Validar / calcular** (determinista, en el servicio):
  - **CVSS**: la IA puede sugerir el **vector**; una **librería** calcula el **score** y el
    severity. El score nunca lo "dice" el modelo.
  - **CWE / CVE / MITRE ATT&CK**: cada identificador sugerido se **verifica contra un catálogo
    local** antes de aceptarlo. Un ID que no existe en el catálogo se **descarta** (o se marca
    como no verificado), **nunca** se muestra como válido.
  - Cualquier otro valor con reglas (formatos, rangos) se valida de forma determinista.
- **Persistir**: solo lo validado se persiste, y lo hace con la **procedencia y el estado** que
  exige el ADR-0003 (nace "pendiente" hasta aceptación/edición humana).

Nunca se presenta al usuario un identificador o un cálculo "inventado" sin haber pasado por esta
validación.

## Consecuencias

**A favor:**

- **Corrección garantizada** de scores e identificadores: el dato duro lo respalda código
  determinista y catálogos, no el modelo.
- **Auditable y reproducible**: la validación no depende del azar del modelo.
- Encaja con los otros principios: la propuesta entra con procedencia (ADR-0003) y con las
  entradas ya redactadas (ADR-0005).

**En contra / costos asumidos:**

- **Requiere catálogos locales**: CWE, MITRE ATT&CK y una **caché de CVE**, además de una
  **librería de cálculo de CVSS**. Hay que incorporarlos, versionarlos y mantenerlos
  actualizados.
  - `[[POR LLENAR: estrategia de obtención/actualización y versionado de los catálogos
    (CWE/ATT&CK/CVE) — se definirá en el ADR de catálogos de su fase]]`.
- Define un **patrón común** ("sugerir → validar → persistir") que todas las funciones de IA de
  clasificación deben seguir; hay que implementarlo una vez y reutilizarlo.
- Introduce un estado posible de "sugerido pero **no verificado**" que la UI debe saber mostrar
  (p. ej. advertir que un ID propuesto no se encontró en el catálogo).

**Alcance:**

- Este ADR fija el principio y el patrón; **no** incorpora dependencias ni catálogos en esta
  tanda. La construcción de catálogos, la librería de CVSS y el gateway de IA corresponden a sus
  fases (F1 en adelante).
