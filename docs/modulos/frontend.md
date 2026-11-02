# Ficha de módulo: frontend (cimientos de UI)

- **Fase / tanda:** F0-T5a (cimientos) + F0-T5b (pantallas de dominio)
- **Estado del módulo:** cimientos de UI + pantallas de workspaces/projects/membresías. Cierra la
  Fase 0 en frontend.
- **Última actualización:** 2026-10-23

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
    home/   pages/HomePage (placeholder post-login)
```

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

## Verificación manual

1. `task up` · `task dev-api` · `task dev-web`; abrir http://localhost:5173.
2. Registrarse → entra a Inicio; recargar → sigue logueado; alternar tema (sin parpadeo, ambos
   correctos); cerrar sesión → vuelve a login; borrar cookies y pedir una ruta protegida → 401 → login.

## Pendiente / `[[POR LLENAR]]`

- Invitación de usuarios nuevos por email (hoy "añadir miembro" opera sobre usuarios existentes).
- Code-splitting del bundle (PrimeReact hace el chunk > 500 kB; aviso informativo de Vite).
- `SameSite=Strict` / endurecimiento CSRF según despliegue (ADR-0010).
- Persistencia de tema por usuario en backend (diferida; no tocar `users`).
- Pantallas de evidencia/hallazgos/documentos y funciones de IA (F1+).
