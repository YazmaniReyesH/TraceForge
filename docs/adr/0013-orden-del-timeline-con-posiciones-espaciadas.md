# ADR-0013: Orden del timeline con posiciones espaciadas (huecos) e índice no único

- **Estado:** aceptado
- **Fecha:** 2026-11-02

## Contexto

El timeline (ADR-0012) nació con `evidence_items.position` como enteros **contiguos** (0, 1, 2…)
y un **`UNIQUE(session_id, position)`**. Eso basta para **añadir al final**, pero F1-T2 necesita
**insertar entre dos** ítems y **reordenar** por arrastre. Con posiciones contiguas, insertar o
mover obliga a **renumerar** (desplazar +1) a todos los ítems siguientes en cada operación: muchas
escrituras, mala concurrencia y fricción con actualizaciones optimistas de la UI.

Además, el `UNIQUE(session_id, position)` **estorba** justo cuando hay que reescribir varias
posiciones a la vez (renumeración, o dos reordenamientos casi simultáneos): los `UPDATE` por fila
pueden chocar de forma **transitoria** aunque el estado final sea válido.

Alternativas consideradas:
- **A. Contiguo + renumerar siempre.** Simple de leer, caro de escribir; no escala a reordenar.
- **B. Fraccionario (float / fracción / string "lexo-rank").** Inserciones casi infinitas sin
  renumerar, pero los `float` pierden precisión y los rangos lexicográficos añaden complejidad.
- **C. Entero con huecos** (múltiplos de ~1000) + inserción "entre dos" por **punto medio** y
  **renumeración controlada** solo cuando un hueco se agota. Simple, entero, y la renumeración es
  rara (con saltos de 1000 caben ~10 inserciones en el mismo punto antes de agotar).

## Decisión

Usaremos **enteros con huecos (opción C)** y un **índice NO único**:

- **Escala:** `POSITION_STEP = 1000`, borde izquierdo virtual `POSITION_BASE = 0`. Añadir al final
  = `max(position) + STEP` (o `STEP` si la sesión está vacía).
- **Insertar "entre dos":** posición = **punto medio** entre el vecino izquierdo y el derecho
  (`(left + right) // 2`). "Al inicio" usa `left = 0`; "al final" usa `right = None` → `left + STEP`.
- **Renumeración controlada:** si no cabe un entero intermedio (`right - left < 2`), se **renumera**
  esa sesión a escala limpia (`1000, 2000, …`) conservando el orden actual, y se recalcula (tras
  renumerar, el hueco es `STEP` y siempre cabe). La renumeración se hace en **dos fases** (primero a
  un rango **negativo** disjunto, luego al final) para no provocar colisiones transitorias.
- **Índice NO único** `ix_evidence_items_session_position (session_id, position)` en vez del
  `UNIQUE`: la unicidad de `position` **no es un invariante de negocio** (era solo un mecanismo de
  orden). Quitarla evita fallos por colisión transitoria al renumerar/reordenar de forma optimista.
- **Orden determinista:** siempre `ORDER BY position, created_at, evidence_item_id`. El desempate por
  `created_at`/`id` garantiza un orden total estable aunque dos ítems compartieran `position`
  (p. ej. por una carrera), sin depender de la unicidad.
- **Reordenar NO versiona:** mover un ítem cambia solo su `position` (metadato de orden); **no** crea
  versión de contenido ni altera hashes (append-only intacto, ADR-0012). Permiso `projects:update`
  (contributor/lead, rol efectivo ADR-0002); aislamiento por project intacto.
- **API desacoplada de los números:** el cliente nunca envía `position`. Indica **vecindad** con
  `after_item_id` (crear con inserción; endpoint `move`): `null` = al inicio, un id = justo después
  de ese ítem, el último id = al final. Así la UI (arrastre) no conoce la escala interna.
- **Migración incremental** (no aplicada por Claude): quita el `UNIQUE`, **rellena** las posiciones
  existentes a la escala con huecos (1000·n por sesión, en el orden actual) y crea el índice no
  único; `downgrade` reconstruye posiciones contiguas 0-based y restaura el `UNIQUE`.

## Consecuencias

**A favor:** insertar y reordenar son **una sola escritura** (sin desplazar vecinos); renumerar es
raro y acotado a una sesión; el índice no único tolera colisiones transitorias y escrituras
optimistas; el orden es determinista por el desempate; la API no filtra la mecánica de huecos.

**En contra / costos:** `position` deja de ser legible como "1,2,3" (son 1000, 2000,…) y pueden
existir empates transitorios (resueltos por el desempate); la renumeración, aunque rara, recorre la
sesión; se pierde la garantía de unicidad a nivel de esquema (aceptable: no era un invariante). La
concurrencia fuerte real (muchos reordenamientos simultáneos) podría necesitar más adelante bloqueo
por sesión o rangos fraccionarios; se deja como posible evolución.
`[[POR LLENAR: estrategia de concurrencia fina si el reordenamiento colaborativo lo exige]]`.

## Alcance

Backend de F1-T2 (checkpoint 1): modelo, servicio, endpoints de inserción/reordenamiento y la
migración. El arrastre en la UI que los consume es el checkpoint 2 de F1-T2.
