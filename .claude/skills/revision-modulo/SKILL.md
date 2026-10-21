---
name: revision-modulo
description: >
  Checklist de "Definición de Terminado" para revisar un módulo de TraceForge antes de
  darlo por cerrado o abrir su Pull Request. Úsala SIEMPRE que el equipo diga que un módulo
  "ya está", "lo terminé", "voy a hacer el PR", "revisa el módulo" o al cerrar cualquier
  fase/tanda/entidad antes de pasar a la siguiente. Verifica capas, fidelidad al modelo de
  datos, seguridad multiusuario, aislamiento por workspace, permisos por campo, auditoría,
  los principios de IA (procedencia, IA-propone/código-valida, redacción, evidencia no
  confiable), pruebas, migraciones y documentación viva actualizada.
---

# Skill: revision-modulo

Recorrer el módulo contra esta lista y reportar cada punto como **OK / Falta / N/A**,
señalando exactamente qué corregir (archivo/línea cuando se pueda). No marcar "terminado" si
algo crítico (seguridad, aislamiento, IA, migraciones, documentación) falta.

## Fidelidad al modelo de datos
- [ ] Nombres de entidades, campos y estados EXACTOS al modelo (ADRs/ficha); sin inventar ni renombrar.
- [ ] Estados con valores exactos y CHECK constraints nombrados.
- [ ] Transiciones de estado validadas (máquina de estados); transición inválida → 409.
- [ ] Campos "Calculado"/"generado por IA validado" solo escribibles por el servicio
      (rechazados si vienen en el request) y solo presentes en `XxxRead`.

## Arquitectura y capas
- [ ] `router` sin lógica ni SQL; `service` con reglas y transacciones; `repository` único
      acceso a BD; respuestas con schemas `XxxRead` (nunca entidades crudas).
- [ ] Frontend espeja la estructura y usa los componentes/patrones compartidos.

## Seguridad y multiusuario (no negociable)
- [ ] Cada endpoint con autenticación + `requiere_permiso(...)` según la matriz RBAC.
- [ ] Rol y **workspace resueltos del token**, nunca del cliente.
- [ ] **Aislamiento por workspace/proyecto**: toda consulta filtra por el workspace del
      usuario; imposible leer/tocar datos de otro workspace.
- [ ] Campos sensibles: verificación de permiso por campo ANTES de modificar.
- [ ] Entradas validadas; sin secretos ni PII en logs; secretos solo en entorno/configuración.

## Principios de IA (si el módulo usa IA)
- [ ] Toda salida de IA se persiste con **procedencia** (proveedor, modelo, versión de prompt,
      fecha, entradas usadas) y nace en estado "pendiente" hasta aceptación/edición del usuario.
- [ ] La IA **propone** y el código **valida/calcula**: CVSS calculado por librería; CWE/CVE/
      ATT&CK verificados contra catálogo local antes de mostrarse (sin IDs inventados).
- [ ] La **evidencia cruda original se conserva** y la narrativa generada no la sustituye.
- [ ] **Redacción de secretos aplicada** antes de cualquier llamada a un proveedor en la nube,
      respetando la política de IA del proyecto.
- [ ] Evidencia **delimitada como dato no confiable** en el prompt; salida con JSON Schema
      estricto y sin herramientas habilitadas para el modelo.
- [ ] Cada llamada de IA queda registrada para auditoría (proveedor, modelo, qué se envió
      ya redactado).

## Auditoría
- [ ] Cambios a campos/parámetros sensibles registran en la bitácora (usuario, fecha, valor
      anterior, valor nuevo, ip).

## Datos / migraciones
- [ ] Esquema solo por migraciones Alembic revisadas (downgrade correcto). La aplica el equipo.
- [ ] PKs `UUID`; `Numeric` para montos; `timestamptz` para fechas; estados `String` + CHECK;
      JSONB para bloques/salidas de IA; FKs explícitas + índices en FKs, `workspace_id` y
      columnas de filtros.

## Pruebas y calidad
- [ ] Backend: pruebas de casos felices, validaciones y transiciones de estado; `mypy` y
      `ruff` sin errores nuevos.
- [ ] Frontend: `tsc --noEmit`, lint y pruebas; sin `any` injustificado; estados de
      carga/error/vacío manejados.

## Documentación viva (bloqueante)
- [ ] `docs/API-CONTRACT.md` actualizado con los endpoints del módulo.
- [ ] `docs/modulos/<modulo>.md` refleja el estado real (entidades, estados, pantallas).
- [ ] Funciones de IA registradas en `docs/ai-tasks.md`; plantillas en `docs/plantillas.md`.
- [ ] Decisiones técnicas registradas como ADR por archivo en `docs/adr/NNNN-titulo.md` y listadas en el índice `docs/arquitectura.md`.
- [ ] Términos nuevos en `docs/glosario.md`.

## Pasos finales
- [ ] Router registrado en `apps/api/app/main.py`; rutas y menú (por área) en el front.
- [ ] PR pequeño, enfocado, con descripción clara y la documentación INCLUIDA.

## Salida esperada
Resumen con: qué está OK, qué falta y un veredicto: **listo para PR** o **bloqueado por: ...**.
