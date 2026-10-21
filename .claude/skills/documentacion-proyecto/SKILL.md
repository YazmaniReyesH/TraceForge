---
name: documentacion-proyecto
description: >
  Mantiene actualizada la documentación viva de TraceForge en docs/ (arquitectura/ADRs,
  API-CONTRACT, GITHUB_WORKFLOW, glosario, fichas de módulo, registro de funciones de IA,
  catálogo de plantillas, política de datos). Úsala SIEMPRE al terminar cualquier tarea de
  desarrollo (endpoint nuevo o modificado, entidad o migración, pantalla, función de IA,
  plantilla de reporte, integración, decisión técnica), antes de abrir un PR, o cuando el
  equipo pida "actualiza la documentación", "documenta esto" o "deja registro". Regla del
  proyecto: un cambio sin su documentación actualizada NO está terminado; el código y su
  documentación viajan en el mismo PR.
---

# Skill: documentacion-proyecto

La documentación de TraceForge es **viva**: se actualiza a la par del código, no al final.
Esta skill define QUÉ documento tocar según el tipo de cambio y CÓMO escribirlo.

## Mapa: tipo de cambio → documento a actualizar

| Si el cambio es... | Actualiza... |
|---|---|
| Endpoint nuevo, modificado o eliminado | `docs/API-CONTRACT.md` (permiso requerido, reglas, ejemplos, errores) |
| Entidad nueva, campo nuevo, migración | `docs/modulos/<modulo>.md` (sección de entidades y estados) |
| Cambio de estados o transiciones | `docs/modulos/<modulo>.md` + nota en `docs/API-CONTRACT.md` si afecta endpoints |
| Pantalla nueva o rediseñada | `docs/modulos/<modulo>.md` (sección pantallas: qué muestra, qué roles la usan) |
| **Función de IA nueva o modificada** (prompt, schema de salida, contexto que lee) | `docs/ai-tasks.md` — registro de "AI Tasks": id, propósito, versión de prompt, JSON Schema, contexto permitido, capacidades requeridas (visión, salida estructurada, contexto), proveedor(es) permitido(s) |
| **Plantilla de reporte nueva o cambiada** | `docs/plantillas.md` (estructura de bloques, estilos, branding, formatos de exportación) |
| **Cambio a la política de datos/redacción o a lo que cruza el perímetro hacia un proveedor** | `docs/seguridad-datos.md` + ADR nuevo en `docs/adr/` si hubo decisión |
| Decisión técnica o de arquitectura | Nuevo **ADR** como archivo propio en `docs/adr/NNNN-titulo.md` (contexto → decisión → consecuencias) y registrarlo en el índice `docs/arquitectura.md` |
| Integración nueva o cambiada (proveedor de IA, importador Nmap/Burp/Nessus, exportador) | ADR nuevo en `docs/adr/` si hubo decisión + `docs/modulos/<modulo>.md` |
| Término de negocio o técnico nuevo o aclarado | `docs/glosario.md` |
| Cambio al flujo de trabajo Git/PRs | `docs/GITHUB_WORKFLOW.md` |
| Cambio a reglas globales del proyecto | `CLAUDE.md` raíz (¡primero!) y los `CLAUDE.md` locales si aplica |

## Cómo escribir

- **En español**, claro y breve. Explica el "por qué", no solo el "qué".
- No dupliques la fuente técnica: el OpenAPI de FastAPI ya documenta las firmas exactas;
  `API-CONTRACT.md` agrega negocio, permisos y ejemplos. Los modelos SQLAlchemy ya definen
  los campos; la ficha del módulo agrega decisiones, pendientes y lo aprendido al implementar.
- **Las funciones de IA siempre quedan registradas en `docs/ai-tasks.md`.** Una función de IA
  sin su entrada en el registro (con prompt versionado y schema) NO está terminada. Esto es lo
  que permite que agregar una función nueva sea agregar una entrada, no inventar un flujo.
- **ADRs**: un ADR por archivo en `docs/adr/NNNN-titulo.md` (numeración consecutiva, formato
  contexto → decisión → consecuencias). `docs/arquitectura.md` es el índice/visión general que
  los lista; no se escriben los ADR dentro de él.
- Marca lo no resuelto como `[[POR LLENAR: ...]]` — nunca lo inventes.
- Si detectas que el código contradice un documento, NO "corrijas" en silencio: repórtalo al
  equipo como inconsistencia a resolver.

## Checklist al cerrar una tarea (antes del PR)

1. ¿Toqué endpoints? → `API-CONTRACT.md` actualizado.
2. ¿Toqué el modelo de datos? → ficha del módulo actualizada (y migración referida).
3. ¿Agregué o cambié una función de IA? → `docs/ai-tasks.md` actualizado (prompt + schema + procedencia).
4. ¿Agregué o cambié una plantilla de reporte? → `docs/plantillas.md`.
5. ¿Toqué lo que se envía a un proveedor de IA o la redacción? → `docs/seguridad-datos.md`.
6. ¿Tomé una decisión técnica con alternativas? → ADR nuevo en `docs/adr/NNNN-titulo.md` y registrado en el índice `docs/arquitectura.md`.
7. ¿Apareció vocabulario nuevo? → `glosario.md`.
8. ¿La ficha `docs/modulos/<modulo>.md` refleja el estado real del módulo?
9. Incluir los archivos de `docs/` modificados EN EL MISMO PR que el código.
