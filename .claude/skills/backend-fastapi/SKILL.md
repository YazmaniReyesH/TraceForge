---
name: backend-fastapi
description: >
  Convenciones para implementar la lógica de backend de TraceForge con Python 3.12,
  FastAPI, Pydantic y SQLAlchemy 2 sobre PostgreSQL. Úsala SIEMPRE que se vaya a escribir
  o modificar código de backend: endpoints, servicios, repositorios, modelos, schemas,
  validaciones, máquinas de estado, RBAC multiusuario, aislamiento por workspace, permisos
  por campo, auditoría, o cualquier función de IA (gateway de proveedores, redacción de
  secretos, tareas de IA con salida estructurada). Asegura el respeto a las capas
  (router → service → repository) y a los dos principios de IA del proyecto.
---

# Skill: backend-fastapi

Cómo implementar un módulo de backend de TraceForge respetando las capas y los principios
fundacionales del proyecto.

## Arquitectura por capas (no romperla)

```
router.py  →  service.py  →  repository.py  →  PostgreSQL
(API/HTTP)    (negocio)       (datos)
```

- **router**: HTTP ↔ negocio. Valida permisos, usa schemas Pydantic, delega TODO al
  servicio. Cero lógica, cero SQL.
- **service**: reglas de negocio, máquinas de estado, permisos por campo, auditoría,
  transacciones, orquestación de IA. No conoce HTTP.
- **repository**: único punto que toca la BD.
- Respuestas con schemas `XxxRead` (nunca entidades SQLAlchemy crudas).

## Multiusuario y aislamiento (desde F0)

TraceForge es multiusuario desde el inicio. Dos fronteras que el backend valida SIEMPRE,
nunca el cliente:

- **Identidad y rol** se resuelven del token (sesión autenticada), nunca del request.
- **Aislamiento por workspace/proyecto**: toda consulta se filtra por el workspace al que
  pertenece el usuario. Un usuario jamás ve ni toca datos de otro workspace. El repository
  recibe el `workspace_id`/`user_id` del contexto autenticado y lo aplica en cada query.
- Endpoints destructivos verifican propiedad antes de borrar en cascada.

## Los dos principios de IA (fundacionales — ver ADRs)

1. **Todo contenido generado por IA es una sugerencia con procedencia.** Al persistir una
   salida de IA se registra: proveedor, modelo, versión del prompt, fecha y las entradas
   usadas (ya redactadas). Nace en estado "pendiente" hasta que el usuario la acepta o edita.
   La narrativa/descripciones generadas NUNCA sustituyen la evidencia cruda original.
2. **La IA propone y el código determinista calcula o valida.** Ejemplos: la IA sugiere un
   vector CVSS → una librería calcula el score; la IA sugiere CWE/CVE/ATT&CK → el servicio
   valida cada ID contra el catálogo local antes de aceptarlo. Nunca mostrar un ID que la IA
   "inventó" sin verificar.

## Gateway de IA y seguridad de datos

- El negocio depende de un **puerto `AIProvider`** (interfaz en términos del dominio), no de
  un SDK concreto. Las implementaciones (Claude ahora; OpenAI/Gemini en F4) viven detrás del
  puerto. Detalle del patrón en la skill `integraciones-externas` cuando exista.
- **Antes de cualquier llamada a un proveedor en la nube**, la evidencia pasa por la capa de
  **redacción de secretos** (contraseñas, hashes, claves privadas, tokens, API keys; PII/IPs
  según política del proyecto). El mapeo marcador→valor real se guarda cifrado; los valores
  reales viven en la evidencia, nunca en la narrativa.
- La política de IA es **por proyecto** (proveedores permitidos, si se envían imágenes,
  redacción on/off según clasificación). El servicio la respeta en cada llamada.
- **La evidencia se delimita como dato NO confiable dentro del prompt** (etiquetada, nunca
  interpolada como instrucción). Los outputs de un objetivo de pentest pueden contener
  inyección de prompt dirigida al modelo; trátalos siempre como contenido hostil.
- Toda llamada de IA se registra para auditoría (proveedor, modelo, qué se envió ya redactado).
- Las tareas de IA usan **salida estructurada (JSON Schema estricto)** y sin herramientas
  habilitadas para el modelo.

## Máquina de estados (patrón obligatorio)

Cada campo de estado tiene su `StrEnum` (en `enums.py`) y un mapa de transiciones en el
servicio. Transición no listada → error de dominio (HTTP 409 desde el router).

```python
class EstadoHallazgo(StrEnum):
    ABIERTO = "abierto"
    REMEDIADO = "remediado"
    RETESTEADO = "retesteado"
    CERRADO = "cerrado"

TRANSICIONES = {
    EstadoHallazgo.ABIERTO: {EstadoHallazgo.REMEDIADO},
    EstadoHallazgo.REMEDIADO: {EstadoHallazgo.RETESTEADO, EstadoHallazgo.ABIERTO},
    # ... completar según el modelo del proyecto; ante duda, confirmar con el equipo
}
```

(Aplica igual a estados de proyecto, de documento y de ítem de evidencia según los ADRs.)

## Endpoint con permiso (patrón)

```python
@router.post("", response_model=HallazgoRead, status_code=201,
             dependencies=[Depends(requiere_permiso("hallazgos:crear"))])
async def crear_hallazgo(data: HallazgoCreate,
                         service: HallazgoService = Depends(get_hallazgo_service)):
    return await service.crear(data)
```

- Todo endpoint nace con su dependencia de permiso. El rol y el workspace salen del token.
- La matriz rol × módulo vive como configuración en `app/core/security.py`, no como ifs
  repartidos.

## Permisos por campo + auditoría

Antes de modificar un campo sensible, verificar permiso por campo y registrar el cambio en
la bitácora de auditoría (usuario, fecha, valor anterior, valor nuevo, ip). Estos hooks
viven en `app/core/` y se usan desde la primera entrega.

## PostgreSQL (notas)

- **PKs**: `UUID` (`gen_random_uuid()` o generación en app — decidir y ser consistentes).
  Nombre `<entidad>_id`.
- **Textos**: `Text`/`String(n)`. **Dinero/decimales**: `Numeric(p,s)`, nunca `float`.
- **Fechas**: `timestamptz` (siempre con zona). **Booleanos**: `Boolean`.
- **Estados**: `String` + **CHECK constraint nombrado** con los valores exactos del enum
  (más fácil de migrar que un enum nativo de Postgres en un producto que evoluciona).
- **JSONB** para documentos de bloques y salidas de IA estructuradas.
- **pgvector** para embeddings (duplicados, búsqueda semántica) cuando el módulo lo requiera.
- FKs explícitas con ON DELETE pensado (RESTRICT por defecto salvo acuerdo); índices en FKs
  y en columnas de filtrado/búsqueda frecuentes.
- `created_at`/`updated_at` donde aplique; `created_by` donde la auditoría lo pida.
- Elegir sync o async y ser **consistente** en todo el backend. Engine/sesión central en
  `app/core/db.py`. Cambios de esquema SOLO por Alembic (skill `migraciones-postgresql`).

## Calidad y cierre

- Tipos + `mypy` (estricto); `ruff` lint; `pytest` de casos felices, validaciones y
  TRANSICIONES de estado.
- Actualizar `docs/API-CONTRACT.md`, la ficha del módulo y, si tocaste IA, `docs/ai-tasks.md`
  (skill `documentacion-proyecto`).
- Pasar `revision-modulo` antes del PR.
