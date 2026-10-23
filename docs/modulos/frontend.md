# Ficha de módulo: frontend (cimientos de UI)

- **Fase / tanda:** F0-T5a
- **Estado del módulo:** cimientos de UI (tema, i18n, cliente HTTP, flujo de auth). Pantallas de
  dominio (workspaces/projects) = F0-T5b.
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

## Verificación manual

1. `task up` · `task dev-api` · `task dev-web`; abrir http://localhost:5173.
2. Registrarse → entra a Inicio; recargar → sigue logueado; alternar tema (sin parpadeo, ambos
   correctos); cerrar sesión → vuelve a login; borrar cookies y pedir una ruta protegida → 401 → login.

## Pendiente / `[[POR LLENAR]]`

- Pantallas de workspaces/projects/membresías (F0-T5b).
- `SameSite=Strict` / endurecimiento CSRF según despliegue (ADR-0010).
- Persistencia de tema por usuario en backend (diferida; no tocar `users`).
