# ADR-0003: Procedencia del contenido generado por IA

- **Estado:** aceptado
- **Fecha:** 2026-10-21

## Contexto

TraceForge usa IA en la nube como motor de asistencia (redactar narrativa de hallazgos,
resumir evidencia, proponer clasificaciones, etc.). En un producto de documentación técnica y
de ciberseguridad, el contenido generado por un modelo **no es una fuente de verdad**: puede
alucinar, puede sesgar y debe quedar siempre subordinado a la **evidencia cruda** y al criterio
humano. Al mismo tiempo, un auditor o un cliente necesita poder **confiar y rastrear** de dónde
salió cada afirmación de un reporte.

Necesitamos una regla fundacional, previa a cualquier función de IA concreta, que determine
**cómo se persiste y se trata** cualquier salida de un modelo. Si no se fija ahora, cada módulo
inventaría su propio flujo y perderíamos trazabilidad y control editorial.

Alternativas consideradas:

- **Tratar la salida de IA como contenido definitivo** (escribirla directamente en el campo
  final): rápido, pero inaceptable: borra la frontera entre lo sugerido y lo validado, y hace
  imposible auditar o revertir.
- **Guardar solo el texto generado, sin metadatos de origen**: impide reproducir, comparar
  versiones de prompt o explicar por qué se dijo algo; mala trazabilidad.
- **Procedencia completa y estado explícito** (la elegida): más campos y disciplina, pero da
  trazabilidad, edición humana y control editorial.

## Decisión

**Todo contenido generado por IA es una sugerencia con procedencia.**

- Al **persistir** una salida de IA se registran, como mínimo, su **procedencia**: proveedor,
  modelo, **versión del prompt**, fecha y las **entradas usadas** (ya **redactadas** según
  ADR-0005).
- La salida **nace en estado "pendiente"** y permanece así hasta que un usuario la **acepta** o
  la **edita**. Solo entonces pasa a formar parte del contenido "humano" del proyecto. El
  cambio de estado y la autoría quedan registrados (auditoría).
- La **evidencia cruda original se conserva siempre** y es inmutable como fuente; la **narrativa
  o descripciones generadas nunca la sustituyen**: conviven, con la evidencia como respaldo.
- La procedencia acompaña a la sugerencia durante toda su vida: aunque un humano la edite, se
  conserva el rastro de que hubo un origen de IA y cuál fue.

Este ADR fija el **principio**; las entidades concretas que lleven contenido de IA (narrativa
de hallazgos, resúmenes, clasificaciones) añadirán los campos de procedencia y estado en la
fase que las implemente, siguiendo esta regla.

## Consecuencias

**A favor:**

- **Trazabilidad**: se puede explicar el origen de cada texto generado y reproducir el contexto
  (versión de prompt, entradas, modelo).
- **Control editorial**: nada generado se da por bueno sin una acción humana explícita
  (aceptar/editar); el estado "pendiente" hace visible lo que falta revisar.
- **Reversibilidad y comparación**: al conservar la evidencia cruda y la procedencia, se puede
  volver atrás o comparar versiones.

**En contra / costos asumidos:**

- Las entidades con contenido de IA necesitan **campos adicionales** (procedencia + estado) y
  una **máquina de estados** mínima (pendiente → aceptado/editado), que se detallará por fase.
- Impacta el diseño de la narrativa y de los hallazgos: la UI debe distinguir claramente lo
  "pendiente de revisión" de lo aceptado, y permitir editar conservando el rastro.
- Más escritura y más almacenamiento (se guarda el origen además del resultado), a cambio de
  auditabilidad.

**Referencias cruzadas:**

- La **redacción** de las entradas registradas se rige por el **ADR-0005**.
- La validación determinista de identificadores/valores sugeridos se rige por el **ADR-0004**.
