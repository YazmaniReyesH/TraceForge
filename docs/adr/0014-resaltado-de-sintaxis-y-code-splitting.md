# ADR-0014: Resaltado de sintaxis (Prism, lazy) y code-splitting del frontend

- **Estado:** aceptado
- **Fecha:** 2026-11-02

## Contexto

El timeline (F1-T2) muestra **comandos** como bloques de terminal con **resaltado de sintaxis**.
Dos fuerzas: (1) el resaltado necesita una librería con gramáticas por lenguaje; (2) el bundle del
frontend ya emitía el aviso de Vite de **chunk > 500 kB** (un único `index.js` de ~780 kB, sobre
todo por PrimeReact). Añadir un resaltador ingenuamente empeoraría el bundle. Además, la skill
`frontend-react` exige **cero colores a mano** (todo por tokens) y el violeta queda reservado a IA.

Alternativas de resaltador:
- **Shiki:** muy preciso (gramáticas TextMate, temas de VS Code), pero su motor + wasm + gramáticas
  pesan varios MB y sus **temas traen su propia paleta** (colores fuera de nuestros tokens).
- **Prism:** núcleo pequeño (~2 kB) + una gramática diminuta por lenguaje; colores controlables por
  CSS, así que podemos **mapearlos a nuestros tokens**; se presta a `import()` dinámico fino.

## Decisión

- **Resaltador: Prism**, cargado **bajo demanda**. El núcleo y **cada gramática** (`bash`, `python`,
  `json`, `sql`, `yaml`, `http`, `markup`) se importan con `import()` dinámico y solo se descargan al
  pintar el primer bloque de comando. El lenguaje se elige por el `language`/`tool` del ítem
  (con alias; `command` sin lenguaje ⇒ `bash`) y **cae a texto plano** si no hay soporte o algo falla.
  Prism arranca en **modo manual** (no escanea el DOM). Los **colores** salen de tokens nuevos
  `--code-*` en `tokens.css` (claro/oscuro), **sin** usar el violeta de IA.
- **Code-splitting de rutas:** todas las páginas se cargan con **`React.lazy` + `Suspense`**, de modo
  que cada pantalla (y su parte de PrimeReact) viaja en un chunk aparte.
- **Justificación de Prism sobre Shiki:** da el **chunk perezoso más pequeño** y permite que el
  resaltado **respete los tokens** del proyecto (regla de identidad visual), frente a Shiki que
  traería un motor pesado y una paleta propia ajena a los tokens.

## Consecuencias

**A favor:** el chunk principal baja de **~780 kB → ~427 kB** y **desaparece** el aviso de > 500 kB;
el resaltador no entra en el bundle principal (solo al usarse); los colores de código son
theme-aware y token-driven; degradación amable a texto plano.

**En contra / costos:** Prism está en modo mantenimiento y sus **componentes de gramática no traen
tipos** (se declara un módulo ambiente `prismjs/components/*`); los componentes se registran sobre un
`Prism` **global** (lo publicamos en `globalThis` antes de importarlos); el conjunto de lenguajes es
acotado (ampliarlo = añadir un `import()` y un alias). Si en el futuro se requiere fidelidad de
resaltado tipo editor, se puede reconsiderar Shiki con su API fina.

## Alcance

Frontend de F1-T2. No cambia el backend ni el contrato de la API.
