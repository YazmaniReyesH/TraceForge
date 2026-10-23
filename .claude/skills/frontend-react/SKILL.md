---
name: frontend-react
description: >
  Convenciones para construir el frontend de TraceForge con React + TypeScript + Vite +
  PrimeReact. Úsala SIEMPRE que se vaya a escribir o modificar código de frontend:
  pantallas, componentes, formularios, tablas, layout, tema claro/oscuro, tokens de
  diseño, cliente HTTP, manejo de sesión/errores, i18n, tipos desde OpenAPI, o la
  visibilidad por rol (RBAC de UX). Define la identidad visual (tokens), el sistema de
  temas, la estructura de módulos de UI y los patrones de pantalla del proyecto.
---

# Skill: frontend-react

Cómo construir pantallas consistentes, accesibles y con la identidad visual de TraceForge.
El backend es la autoridad de seguridad; el frontend es experiencia de usuario.

## Identidad visual: tokens de diseño (fuente ÚNICA de verdad)

**Regla dura:** ningún componente usa colores, fuentes, espaciados ni radios "a mano".
TODO sale de **tokens** (variables CSS en `:root`, con su variante en `.theme-dark`),
centralizados en `src/shared/theme/tokens.css` (o equivalente). Cambiar la identidad
visual = tocar los tokens, nunca las pantallas. PrimeReact se cablea a estos tokens.

Dirección: **base sobria + un acento teal con autoridad + toques "cyber" con propósito.**
Llamativa pero seria; el riesgo va en los detalles que significan algo (estados de IA,
severidad, comandos), no en saturar de neón.

### Paleta — valores canónicos

**Claro (por defecto):**

| Token | Valor | Uso |
|---|---|---|
| `--surface-app` | `#F7F9FB` | fondo de la app |
| `--surface-card` | `#FFFFFF` | tarjetas, paneles, tablas |
| `--surface-raised` | `#EEF2F6` | zonas elevadas/hover sutil |
| `--border` | `#E2E8F0` | bordes y separadores |
| `--text-strong` | `#0F172A` | texto principal |
| `--text` | `#334155` | texto normal |
| `--text-muted` | `#64748B` | texto secundario |

**Oscuro:**

| Token | Valor | Uso |
|---|---|---|
| `--surface-app` | `#0A0E14` | fondo (slate casi negro, tinte azul) |
| `--surface-card` | `#111826` | tarjetas, paneles |
| `--surface-raised` | `#1A2233` | zonas elevadas/hover |
| `--border` | `#223049` | bordes y separadores |
| `--text-strong` | `#E6EDF3` | texto principal |
| `--text` | `#C2CEDB` | texto normal |
| `--text-muted` | `#7E8CA0` | texto secundario |

**Acentos (ambos temas, ajustando luminosidad):**

| Token | Claro | Oscuro | Uso |
|---|---|---|---|
| `--accent` (marca/acción) | `#0E9AA3` | `#22D3DB` | botón primario, enlaces, activo |
| `--accent-contrast` | `#FFFFFF` | `#04121A` | texto sobre el acento |
| `--focus-ring` | `#14C0C9` | `#2CE6EF` | anillo de foco (borde fino luminoso) |
| `--ai` (IA / sugerido) | `#7C5CFF` | `#9D86FF` | contenido generado por IA, "pendiente" |

El acento teal se usa **con disciplina** (acciones primarias, foco, estado activo), no por
todos lados. El violeta `--ai` queda **reservado** a estados de IA (ver "Contenido de IA").

### Severidad (escala semántica — parte de la identidad, no decoración)

Para hallazgos/CVSS. Un token por nivel, legible en claro y oscuro:

| Nivel | Token | Claro / Oscuro |
|---|---|---|
| Crítico | `--sev-critical` | `#C1123F` / `#FF4D6D` |
| Alto | `--sev-high` | `#E5484D` / `#FF6B6B` |
| Medio | `--sev-medium` | `#D9930B` / `#F5B13D` |
| Bajo | `--sev-low` | `#1C7ED6` / `#4DABFF` |
| Informativo | `--sev-info` | `#64748B` / `#8A98AC` |

### Estados semánticos

`--success` `#2F9E44`/`#51CF66`, `--warning` `#D9930B`/`#F5B13D`, `--danger`
`#E03131`/`#FF6B6B`, `--info` = `--accent`. Siempre acompañar el color con icono/texto
(nunca color como único portador de significado — accesibilidad).

### Tipografía, espaciado, forma

- **UI:** `Inter` (fallback `system-ui, sans-serif`). **Monoespaciada:** `JetBrains Mono`
  (fallback `IBM Plex Mono, monospace`) para **comandos, outputs, hashes, CVE/CWE, IDs** —
  son protagonistas en esta app; trátalos con cariño (fondo `--surface-raised`, `--border`).
- Fuentes vía `@fontsource` o Google Fonts con fallback real; nunca bloquear el render.
- Escala de espaciado por tokens (`--space-1..8`), radios (`--radius-sm/md/lg`), y sombras
  **sutiles** (en oscuro, preferir borde luminoso tenue sobre sombra). El guiño "cyber" va
  en foco/hover (borde fino `--focus-ring`), no en adornos permanentes.

## Tema claro/oscuro

- **Arranca en CLARO** por defecto. Toggle manual claro↔oscuro.
- **Persistencia:** `localStorage` (clave p. ej. `tf-theme`). La persistencia por usuario en
  backend queda diferida (mejora futura; no tocar `users` ahora).
- **Anti-parpadeo (obligatorio):** un script inline mínimo en `index.html`, ANTES de que
  React pinte, lee `localStorage` y aplica la clase de tema al `<html>`. Sin esto, al
  recargar en oscuro se ve un destello claro. Es requisito de calidad, no opcional.
- Implementación: clase `theme-dark` en `<html>` (o `data-theme`), y PrimeReact apuntando a
  los tokens. Un `ThemeProvider`/hook expone el tema actual y el toggle.
- Toda pantalla debe verse correcta en **ambos** temas (revisarlo siempre).

## Estructura de módulos de UI (espeja el backend)

```
src/
├── modules/<modulo>/
│   ├── types.ts      # tipos alineados al backend (generados de OpenAPI)
│   ├── api.ts        # llamadas a /api/v1/<modulo>
│   ├── hooks.ts      # queries / mutations (TanStack Query)
│   ├── components/
│   └── pages/
└── shared/
    ├── ui/           # componentes reutilizables (se construyen UNA vez)
    ├── theme/        # tokens.css, ThemeProvider
    ├── api/          # cliente HTTP, manejo de errores/401
    └── i18n/         # configuración y catálogos de traducción
```

- **Tipos desde OpenAPI** (`openapi-typescript`): el front NO redefine a mano los DTOs del
  backend; se generan para no desincronizarse. Regenerar cuando cambie el contrato.
- Lo reutilizable (layout, tabla con toolbar, panel de detalle, badges, modal de
  confirmación, estados vacío/carga/error) vive en `src/shared/ui` y se construye una vez.

## Patrones de pantalla

1. **Lista + panel de detalle:** tabla a la izquierda (búsqueda, filtros, contador); al
   seleccionar un renglón se abre un panel de detalle (~480px) para ver/editar sin perder
   contexto. Patrón por defecto de catálogos y listados (workspaces, projects, miembros).
2. **Form full-screen con secciones:** para capturas complejas (más adelante: hallazgos,
   documentos). Secciones con navegación por anclas y guardado por etapa.
3. **Manejo explícito de carga / error / vacío en CADA pantalla.** Nunca una tabla en
   blanco sin explicar si está cargando, falló o no hay datos. Son componentes de
   `shared/ui`, no improvisados por pantalla.
4. PrimeReact `DataTable` para tablas; respeta tokens (sin estilos de color inline).

## Cliente HTTP y sesión

- La sesión es **cookie httpOnly** (ver auth del backend): todas las llamadas van con
  `credentials: "include"`. No se lee ni se guarda el token en JS (es httpOnly por diseño).
- Al arrancar, hidratar la sesión con `GET /api/v1/auth/me`; si da 401, el usuario no está
  autenticado → a login.
- **Manejo global de 401:** un interceptor lleva a login y limpia el estado de sesión.
- **CSRF:** cuando se habilite el token anti-CSRF (previsto en F0-T5a), el cliente debe
  enviarlo en las mutaciones (patrón double-submit o el que defina su ADR). Hasta entonces,
  la protección es `SameSite=Lax` + la regla de que **ningún GET muta**.
- **Alcance por ruta:** los recursos de workspace/proyecto llevan el id en la URL
  (`/workspaces/{id}/projects/...`), coherente con el backend; el front nunca "inventa" un
  workspace activo por su cuenta.

### Errores → mensajes

- Mapear los errores del backend a mensajes claros en español (vía i18n). Respetar los
  códigos del contrato: **401** (no autenticado → login), **403** (sin permiso → mensaje,
  no redirigir), **404** (no encontrado o sin acceso → mensaje genérico, NO revelar
  existencia), **409/422** (conflicto/validación de negocio → mostrar el detalle).
- `[[POR LLENAR: convención de códigos de error de negocio del backend]]` — se está
  unificando en F0-T5a (p. ej. guest=viewer responde hoy 422; puede pasar a 409). Alinear
  el mapeo de mensajes cuando se cierre esa convención; no hardcodear supuestos frágiles.
- Invalidar queries tras cada mutación; deshabilitar submit mientras envía; mostrar errores
  del servidor (incluido 409/422 de reglas de negocio, con mensaje entendible).

## RBAC en el frontend = solo UX

- El backend valida SIEMPRE; el front solo **muestra/oculta/deshabilita** según el rol para
  mejorar la experiencia. Nunca es una barrera de seguridad.
- Un recurso al que el usuario no tiene acceso devuelve **404** desde el backend (no revela
  existencia); la UI lo trata como "no encontrado", sin asumir que existe.
- Ocultar acciones que el rol no permite (p. ej. "transferir propiedad" solo para owner),
  pero asumir que el backend rechazará igualmente si se intentara.

## Internacionalización (i18n) — preparada desde el inicio

- **Idioma actual: español (es-MX).** Pero NINGÚN texto visible va hardcodeado en los
  componentes: todo pasa por claves de traducción (p. ej. `t("workspaces.create")`).
- Catálogos en `src/shared/i18n/<lang>/...`. Estructura lista para sumar idiomas sin
  reescribir componentes (la app será pública). Formatos de fecha/número vía la librería de
  i18n, no manuales.
- Textos de error, vacío, confirmaciones y validaciones también por i18n.

## Contenido generado por IA en la UI (ADR-0003 / ADR-0004)

- El contenido sugerido por IA se muestra **claramente diferenciado** del contenido humano:
  usa el acento `--ai` y un badge de estado "pendiente de revisión" hasta que el usuario lo
  acepte o edite. Nunca presentar una sugerencia de IA como si fuera contenido validado.
- La **evidencia cruda** se muestra tal cual (monoespaciada), nunca sustituida por la
  narrativa generada.
- Identificadores sugeridos (CWE/CVE/ATT&CK) solo se muestran como válidos si el backend los
  validó (ADR-0004); un "sugerido no verificado" debe verse distinto (advertencia).

## Reglas

- **TypeScript estricto**; nada de `any` sin justificación escrita.
- Tipos desde OpenAPI; el front no renombra ni inventa campos del backend.
- Cero colores/tipografías/espaciados hardcodeados: todo por tokens.
- Accesibilidad: contraste suficiente en ambos temas; foco visible; color nunca como único
  portador de significado; navegación por teclado en controles.
- Estados de carga/error/vacío siempre manejados.
- Moneda/fechas/números por i18n; textos es-MX por claves.

## Cierre

`tsc --noEmit`, lint (eslint + prettier) y pruebas pasan; verificar la pantalla en **tema
claro y oscuro**; actualizar la ficha del módulo en `docs/modulos/` (skill
`documentacion-proyecto`); luego `revision-modulo`.
