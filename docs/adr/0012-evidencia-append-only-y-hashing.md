# ADR-0012: Evidencia append-only, versionada y con hash de contenido

- **Estado:** aceptado
- **Fecha:** 2026-11-01

## Contexto

La Fase 1 introduce el **timeline**: una bitácora cronológica de evidencia dentro de un project
(F1-T1, solo backend). La evidencia es el insumo crudo de una auditoría/pentest/CTF, y sobre ella
se construirán hallazgos y narrativa de IA en fases siguientes. Dos principios fundacionales la
condicionan: la **evidencia cruda nunca se sustituye por narrativa generada** y todo contenido de
IA es una **sugerencia con procedencia** (ver ADR-0003/0004). Para que eso tenga sentido, la
evidencia debe tener **cadena de custodia**: qué se capturó, cuándo, y que no se alteró en
silencio.

En F1 solo hay evidencia **de texto**, de dos tipos (`kind`): `command` (comando + output) y
`note` (texto libre). Hace falta decidir: (1) cómo se corrige/edita sin perder lo anterior;
(2) cómo se "borra" sin destruir la bitácora; (3) cómo se detecta/verifica una alteración;
(4) un tope de tamaño razonable.

Alternativas consideradas para el versionado:
- **A. Una sola fila mutable** por ítem (UPDATE directo). Simple, pero destruye la cadena de
  custodia: una corrección pisa la evidencia original.
- **B. Columna `version` + histórico en la misma tabla** (fila "vigente" marcada). Mezcla lo
  mutable y lo inmutable en una tabla; fácil de violar por accidente (un UPDATE a la fila
  equivocada).
- **C. Dos tablas**: un ítem lógico (mutable: puntero a versión vigente, posición, soft-delete) y
  sus **versiones inmutables** (append-only). La inmutabilidad se vuelve física: el contenido
  vive solo en filas que nunca se hacen UPDATE.

## Decisión

Usaremos el **modelo de dos tablas (opción C)**:

- **`evidence_items`** — ítem lógico, mutable solo en metadatos: `position` (orden), `kind`,
  `current_version` (puntero a la versión vigente), `deleted_at` (soft-delete), `created_by`.
- **`evidence_item_versions`** — **append-only, inmutable**: `version` (1,2,3…), `content_hash`,
  `captured_at`, el contenido (`command_text`/`command_output`/`note_text`) y pistas de
  presentación (`tool`/`language`). UNIQUE `(evidence_item_id, version)`.

Reglas:
- **Editar = versión nueva.** "Corregir" un ítem inserta una fila de versión nueva y mueve el
  puntero `current_version`; **la versión anterior se conserva con su hash**. El contenido de una
  versión **nunca** se hace UPDATE. El `kind` **no** puede cambiar al editar (una nota no se
  convierte en comando) → error `evidence_kind_mismatch` (409).
- **Borrar = soft-delete.** `DELETE` marca `deleted_at`; **nunca** hay borrado físico. El ítem
  deja de listarse/leerse pero la fila y su historial permanecen (cadena de custodia).
- **Hash de contenido (SHA-256).** Cada versión guarda `content_hash` = SHA-256 sobre los **bytes
  UTF-8** de un **JSON canónico** del *contenido* de la evidencia (no de su presentación):
  - `command` → `{"command":<texto>,"kind":"command","output":<texto>}`
  - `note` → `{"kind":"note","text":<texto>}`

  Canónico = `json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",",":"))` (claves
  ordenadas, sin espacios). Campos ausentes se normalizan a `""`. **`tool` y `language` NO entran
  en el hash** (son pistas de presentación, no evidencia). Así cualquier verificador recomputa el
  mismo hash con la misma regla; el `content_hash` es determinista y auto-verificable.
- **Tope de tamaño.** Cada campo de texto se limita a **1 000 000 caracteres** (~1 MB en UTF-8 de
  1 byte) a nivel de schema (422 si se excede). Generoso para outputs de escaneos grandes, pero
  acota el tamaño de request/fila y evita abuso; evidencia mayor pertenecerá a almacenamiento de
  objetos (diferido en F1).
- **Reservas (no se modelan en F1-T1, se dejan previstas):** el `content_hash` por versión es el
  gancho sobre el que colgará el contenido de IA con procedencia (ADR-0003) y los hallazgos
  (futuros), que referenciarán **versiones** concretas de evidencia, no el ítem mutable.

## Consecuencias

**A favor:** la inmutabilidad del contenido es **física** (no depende de disciplina de código: el
contenido solo existe en filas que nunca se actualizan); cadena de custodia completa (historial +
hash por versión); el soft-delete preserva la bitácora; el hash permite detectar alteraciones y
deduplicar; `tool`/`language` pueden cambiar sin invalidar el hash de la evidencia.

**En contra / costos:** dos tablas y un `JOIN` (ítem + versión vigente) para listar; el puntero
`current_version` es *bookkeeping* que hay que mantener coherente en el servicio; el hash no es una
firma criptográfica (no prueba *quién* lo capturó ni impide reescribir la fila con permisos de BD);
el soft-delete acumula filas (sin purga en F1). El borrado físico real (retención/GDPR) y la
verificación de integridad periódica quedan como función futura.
`[[POR LLENAR: política de retención/purga de evidencia borrada]]`.

## Alcance

Backend de F1-T1 (modelo + migración + CRUD mínimo append-only). La UI del timeline es F1-T2; las
funciones de IA sobre evidencia, F1-T3/T4. Sin binarios/archivos (almacenamiento de objetos
diferido).
