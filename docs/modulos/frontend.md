# Ficha de módulo: frontend (cimientos de UI)

- **Fase / tanda:** F0-T5a (cimientos) + F0-T5b (pantallas de dominio) + F1-T2 (timeline)
- **Estado del módulo:** cimientos de UI + pantallas de workspaces/projects/membresías + **timeline
  de evidencia** (captura, reorden por arrastre, historial) con resaltado de sintaxis lazy.
- **Última actualización:** 2026-11-05

## Propósito

Montar la base del frontend según la skill `frontend-react`: identidad visual por tokens, tema
claro/oscuro sin parpadeo, PrimeReact cableado a los tokens, i18n (es-MX), cliente HTTP con CSRF
y manejo de 401/errores, enrutado con área protegida, y el flujo real de login/registro/logout.

## Stack de UI

PrimeReact + primeicons, TanStack Query, react-router-dom, i18next + react-i18next, @fontsource
(Inter + JetBrains Mono), openapi-typescript (dev). Vite con **proxy** `/api`→backend en dev
(same-origin → cookies + CSRF sin CORS).

## Estructura (espeja el backend)

```
src/
  main.tsx                 # fuentes, CSS, PrimeReact, i18n, Query, Router, Theme; 401 global
  App.tsx                  # rutas públicas (/login,/register) + área protegida
  shared/
    theme/  tokens.css (FUENTE ÚNICA), ThemeProvider, useTheme, themeStorage, primeTheme
    api/    client.ts (fetch: credentials+CSRF+errores), errors.ts (ApiError+i18n), types.gen.ts
    i18n/   index.ts, es-MX.ts (catálogo; sin textos hardcodeados)
    ui/     AppLayout, ThemeToggle, PageLoader, layout.css
  modules/
    auth/   api.ts, hooks.ts, types.ts, components/ProtectedRoute, pages/Login, pages/Register
    workspaces/ · projects/ · me/   # pantallas de dominio (F0-T5b)
    timeline/   api.ts, hooks.ts, types.ts, timeline.css, components/, pages/TimelinePage (F1-T2)
```

> **Code-splitting (F1-T2):** las páginas se cargan con `React.lazy` + `Suspense` (cada pantalla y
> su parte de PrimeReact viajan en chunks aparte). El resaltador de sintaxis (Prism) y sus
> gramáticas se cargan con `import()` dinámico solo al pintar el primer comando. Resultado: el
> chunk principal bajó de **~780 kB → ~427 kB** y desapareció el aviso de Vite de chunk > 500 kB.

## Tema claro/oscuro

- **Tokens** (`tokens.css`) = fuente única (claro en `:root`, oscuro en `.theme-dark`). Ningún
  color/fuente/espaciado a mano.
- **Arranca en CLARO**; toggle persistente en `localStorage` (`tf-theme`).
- **Anti-parpadeo:** script inline en `index.html` aplica la clase de tema antes de pintar.
- **PrimeReact sobre los tokens:** preset **Lara teal** (claro/oscuro) intercambiado al alternar
  (`primeTheme.ts`), y un **puente** en `tokens.css` fuerza NUESTRA paleta (acento + superficies)
  sobre Lara con `!important` → sin paleta divergente, en ambos temas. (Decisión: Lara aporta el
  estilado de componentes y la variante oscura correcta; nuestros tokens mandan en el color.)

## Cliente HTTP, sesión y errores

- `credentials: "include"` (cookie de sesión httpOnly). Rutas relativas `/api/v1/...` (proxy).
- **CSRF (ADR-0010):** en mutaciones envía `X-CSRF-Token` con la cookie `tf_csrf`.
- **Errores (ADR-0009):** `ApiError{code,status}`; `apiErrorMessage(code)` → mensaje i18n.
- **401 global:** `QueryCache`/`MutationCache` limpian la sesión (`me`→null) → el guard lleva a
  `/login`. `GET /auth/me` con 401 devuelve `null` (no autenticado), no es error.

## Flujo de auth

- `useMe` hidrata con `GET /auth/me`. `ProtectedRoute` muestra loader mientras carga; sin sesión
  → `/login`. `useLogin`/`useRegister` (registro + login automático) fijan `me`; `useLogout`
  limpia la sesión. Login/registro muestran errores por `code` vía i18n; submit deshabilitado
  mientras envía.

## i18n

- es-MX (catálogo `es-MX.ts`); **cero textos hardcodeados** (claves `t(...)`). Estructura lista
  para más idiomas. Mensajes de error por `code` en `errors.*`.

## Tipos desde OpenAPI

- `src/shared/api/types.gen.ts` **generado** y **commiteado**. Regenerar con **`task gen-types`**
  (vuelca el OpenAPI del backend y corre `openapi-typescript`). CI solo lo typechea (no depende
  del backend en el job de frontend).

## Pantallas de dominio (F0-T5b)

- **`modules/workspaces`** y **`modules/projects`** (cada uno: `types.ts`, `api.ts`, `hooks.ts`,
  `components/`, `pages/`), espejando el backend.
- **Patrón lista + detalle:** `DataTable` a la izquierda; al seleccionar una fila se abre un
  `Sidebar` (~480px) de detalle sin perder contexto. Rutas: `/workspaces`,
  `/workspaces/:id` (abre panel), `/workspaces/:id/projects`, `.../projects/:projectId`.
- **Workspaces:** listar/crear/editar nombre/eliminar (borrado protegido → `409 workspace_not_empty`
  con mensaje accionable); miembros: listar/añadir/cambiar rol/quitar/**transferir propiedad**.
- **Projects:** listar (según acceso efectivo)/crear/editar/eliminar; miembros con **guest=viewer**
  como UX. `classification`/`ai_policy` solo lectura (reservados; sin controles de IA).
- **Permisos como UX:** "mi rol" se deriva de la lista de miembros + `/auth/me`
  (`useMyWorkspaceRole`, `useMyEffectiveProjectRole`). Se ocultan/deshabilitan acciones según rol
  (p. ej. *Eliminar workspace* y *Transferir propiedad* solo para owner), y el backend manda igual.
- **Errores por `code`** vía i18n (p. ej. `workspace_not_empty`, `sole_owner`, `guest_must_be_viewer`,
  `user_not_found`); un recurso sin acceso → 404 → "no encontrado". Confirmaciones (`confirmDialog`)
  para acciones destructivas; queries invalidadas tras cada mutación; submit deshabilitado al enviar.

### "Mis proyectos" y degradación para guest (F0-T5b)

- **`modules/me`** (`MyProjectsPage`, ruta `/projects`, entrada en la navegación del shell visible
  para todos) lista `GET /api/v1/me/projects`: tabla con **nombre del project**, **nombre del
  workspace** (columna de contexto, no opcional: la lista mezcla workspaces) y un **badge de rol
  efectivo**. Cada fila abre el detalle del project existente. Es la vía para que un **guest**
  llegue a su proyecto sin entrar al workspace (no tiene `workspaces:read`).
- **Degradación amable del 403:** si el detalle del workspace responde **403** (guest), el panel
  muestra un mensaje por i18n (`workspaces.noManageAccess`) con botón **"Ir a Mis proyectos"** en
  vez del error crudo.
- **Fix de contraste del dropdown:** Lara **hardcodea** el ítem seleccionado del Dropdown
  (`.p-dropdown-item.p-highlight`) con `color` y `background` ambos `#0f766e` (teal sobre teal →
  ilegible), **sin** usar variables; por eso no se arregla solo con tokens. Se sobreescriben las
  reglas desde el puente (tokens.css) con `!important`: **seleccionado** = `--accent` +
  `--accent-contrast` (misma pareja que el botón primario); **hover/focus no seleccionado** =
  `--accent-subtle` (teal tenue, token nuevo para claro/oscuro) + `--text-strong`. Así el
  seleccionado se lee claramente y el hover se distingue de él, en ambos temas y en los dropdowns
  de rol de workspace y de proyecto.
- **Resaltado de navegación exacto por sección** (no por prefijo amplio): "Workspaces" se activa
  solo en `/workspaces` y `/workspaces/:id`; "Mis proyectos" en `/projects`; el detalle de
  proyecto (`/workspaces/:id/projects/:pid`) no marca ningún menú que no corresponda.

## Timeline de evidencia (F1-T2)

- **`modules/timeline`** (espeja el backend: `types.ts` desde OpenAPI, `api.ts`, `hooks.ts`,
  `components/`, `pages/TimelinePage`). Ruta dentro del project:
  `/workspaces/:wid/projects/:pid/timeline[/:sessionId]`; entrada desde el detalle del project.
- **Pantalla:** lista/selector de **sesiones** (crear, renombrar, soft-delete con confirmación) +
  **timeline** de la sesión activa (auto-selecciona la primera). Estados de carga (skeletons con la
  forma del riel), error y vacío.
- **Dirección visual (consola de operador, "cyber" dosificado):** riel cronológico con glow teal
  (tenue; sobre todo en oscuro), **nodo activo** (el más reciente) con halo; **bloque de comando**
  tipo terminal (prompt `$` en teal, barra de acento a la izquierda, resaltado de sintaxis, output
  distinguible y **colapsable**, **copiar** en hover); **nota** con identidad propia (Inter, acento
  lateral e icono); **metadatos** en monoespaciada como telemetría (hora, hash corto, versión);
  microinteracción **scanline** (~300 ms, una vez) al capturar; feedback de "copiado". **Regla de
  contención:** glow/animaciones en acentos y sobre todo en oscuro; en claro, atenuado; nada de
  efectos sobre texto de lectura larga; **`prefers-reduced-motion`** desactiva animaciones. El
  violeta de IA **no** aparece (reservado a F1-T4).
- **Layout de dos columnas (aprovecha el ancho):** la pantalla **sangra** fuera del contenedor de
  960px del shell (`.tf-tl-page`: `width: min(1360px,94vw)` centrada) para usar el ancho disponible.
  **Sidebar** de sesiones **sticky** (persistente al hacer scroll, más ancho = 280px) + **columna
  principal** amplia con `minmax(0,1fr)` (los outputs no desbordan). Los bloques de comando/salida
  (mono) usan el ancho amplio; las **notas** se limitan a ~82ch para lectura cómoda. Responsive: a
  ≤980px se desactiva la sangría; a ≤860px una sola columna con el sidebar arriba (no sticky).
- **Captura ágil (barra compacta):** barra **sticky** inferior, **sólida** y la columna reserva
  `padding-bottom` para que no tape el último ítem. El fondo usa un token **opaco literal**
  `--capture-bg` (`#ffffff`/`#111826`), **no** `--surface-card`: el puente de PrimeReact define
  `--surface-card: var(--surface-card)` (cíclico → el valor queda inválido → `transparent`), lo que
  transparentaba la barra sobre el timeline (visible sobre todo en oscuro); con el token literal el
  fondo es 100% opaco. Sombra superior marcada (`--capture-shadow`) + línea de acento la despegan. En **reposo** solo muestra **"+ Comando / + Nota"**; al pulsar **expande** el
  formulario con ese tipo; tras guardar sigue abierta (captura en serie) y se limpia; "Cancelar" la
  pliega. El nodo nuevo entra con scanline. Validación/errores por `code`.
- **Reordenar/insertar por arrastre:** HTML5 drag-and-drop; soltar en la mitad superior/inferior de
  un nodo inserta antes/después (→ `after_item_id`); estado **optimista** con reconciliación (si el
  backend falla, revierte y muestra el error). Viewer **no** ve controles de edición/orden.
- **Copiar por sección:** botones independientes (hover + feedback "copiado") en **comando**,
  **salida** (dos botones en el bloque de comando) y **nota**.
- **Historial:** marcador "editado · ver historial" (si `version > 1`) abre el rastro de versiones
  con su **hash corto** en un modal holgado (`min(860px,96vw)`, alto hasta 72vh, más aire por
  versión); "editar" crea versión nueva (backend append-only).
- **Borrado de sesión sin fantasma:** al borrar la sesión activa, reposiciona en la **anterior**
  existente (o la siguiente, o el estado vacío si no queda ninguna); los nombres no se cortan
  (sidebar más ancho + elipsis con **tooltip** para los muy largos).
- **Realce semántico de entidades (determinista, NO IA):** además del resaltado de lenguaje de
  Prism, una capa por **regex** realza entidades de seguridad **en comando y salida**, tomando cada
  una como **unidad** (p. ej. la IP completa, que Prism partiría). Entidades y tokens `--sem-*`:
  IPv4/IPv6 (`--sem-ip`), puerto `N/tcp|udp|sctp` (`--sem-port`), estados open/closed/filtered
  (`--sem-state-*`), `CVE-AAAA-N` (`--sem-cve`), hashes md5/sha1/sha256 por longitud hex
  (`--sem-hash`), rutas absolutas (`--sem-path`). **Convive con Prism** porque el texto se parte en
  `[entidad | resto]`: la entidad se envuelve aquí y Prism resalta solo el "resto" (ver detalle y
  patrones en [`timeline.md`](./timeline.md)). Síncrono (sin lazy) para la salida; para el comando se
  pinta semántico al instante y se **mejora** con Prism al cargar. Peso 600 como pista secundaria
  (el color no es el único indicador). Fallback a texto plano intacto.
- **Tokens nuevos** (en `tokens.css`): superficie/borde de terminal (`--term-*`), glow/halo/scanline
  del timeline, paleta de **sintaxis** (`--code-*`) y de **realce semántico** (`--sem-*`) por tema —
  nada de colores a mano ni violeta de IA. **Resaltado de sintaxis:** **Prism** (ADR-0014) lazy.

## Verificación manual

1. `task up` · `task dev-api` · `task dev-web`; abrir http://localhost:5173.
2. Registrarse → entra a Inicio; recargar → sigue logueado; alternar tema (sin parpadeo, ambos
   correctos); cerrar sesión → vuelve a login; borrar cookies y pedir una ruta protegida → 401 → login.
3. **Timeline:** abrir un project → "Abrir timeline"; crear sesión; capturar un comando (con tool/
   language → resaltado) y una nota; colapsar/expandir output; copiar; reordenar por arrastre;
   insertar entre dos; editar (ver "editado" + historial con hash); ambos temas; `prefers-reduced-motion`.

## Pendiente / `[[POR LLENAR]]`

- Invitación de usuarios nuevos por email (hoy "añadir miembro" opera sobre usuarios existentes).
- `SameSite=Strict` / endurecimiento CSRF según despliegue (ADR-0010).
- Persistencia de tema por usuario en backend (diferida; no tocar `users`).
- Pantallas de hallazgos/documentos y funciones de IA (F1-T3/T4); el violeta `--ai` entra ahí.
