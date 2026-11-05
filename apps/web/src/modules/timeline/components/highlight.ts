// Resaltador de sintaxis cargado BAJO DEMANDA (code-splitting): Prism y cada gramática viven en
// chunks aparte que solo se descargan cuando se pinta el primer bloque de comando. Así el bundle
// principal no carga el resaltador. Los COLORES salen de nuestros tokens (ver timeline.css); aquí
// solo se produce el HTML con clases `token` de Prism, sobre el que se superpone el realce
// semántico (ver semantic.ts): las entidades se envuelven como unidad y Prism resalta solo el resto.

import { escapeHtml, semClass, splitBySemantic } from "./semantic";

// Prism (CJS) expone el objeto en el default del módulo; sus componentes de lenguaje se registran
// sobre un `Prism` global, por eso lo publicamos en globalThis antes de importarlos.
interface PrismLike {
  languages: Record<string, unknown>;
  highlight: (code: string, grammar: unknown, language: string) => string;
}

let prismPromise: Promise<PrismLike> | null = null;
const loadedLangs = new Map<string, Promise<void>>();

// Alias de lenguaje → gramática de Prism que tenemos disponible (import estático analizable).
const GRAMMARS: Record<string, () => Promise<unknown>> = {
  bash: () => import("prismjs/components/prism-bash"),
  python: () => import("prismjs/components/prism-python"),
  json: () => import("prismjs/components/prism-json"),
  sql: () => import("prismjs/components/prism-sql"),
  yaml: () => import("prismjs/components/prism-yaml"),
  http: () => import("prismjs/components/prism-http"),
  markup: () => import("prismjs/components/prism-markup"),
};

const ALIASES: Record<string, keyof typeof GRAMMARS> = {
  bash: "bash",
  sh: "bash",
  shell: "bash",
  zsh: "bash",
  console: "bash",
  python: "python",
  py: "python",
  json: "json",
  sql: "sql",
  yaml: "yaml",
  yml: "yaml",
  http: "http",
  html: "markup",
  xml: "markup",
  markup: "markup",
};

/** Normaliza un lenguaje a una gramática soportada; null si no hay soporte (→ texto plano). */
export function resolveLanguage(language: string | null | undefined): keyof typeof GRAMMARS | null {
  if (!language) return null;
  return ALIASES[language.trim().toLowerCase()] ?? null;
}

async function ensurePrism(): Promise<PrismLike> {
  if (!prismPromise) {
    prismPromise = (async () => {
      // Modo manual ANTES de importar: Prism lee globalThis.Prism.manual al inicializar y así no
      // escanea el DOM solo (nosotros resaltamos a mano con Prism.highlight).
      (globalThis as { Prism?: { manual: boolean } }).Prism = { manual: true };
      const mod = await import("prismjs");
      const prism = ((mod as { default?: PrismLike }).default ?? mod) as PrismLike;
      (globalThis as { Prism?: PrismLike }).Prism = prism; // los componentes lo necesitan global
      return prism;
    })();
  }
  return prismPromise;
}

async function ensureLanguage(lang: keyof typeof GRAMMARS): Promise<void> {
  let loader = loadedLangs.get(lang);
  if (!loader) {
    loader = ensurePrism().then(async () => {
      await GRAMMARS[lang]();
    });
    loadedLangs.set(lang, loader);
  }
  return loader;
}

/**
 * HTML del comando: realce semántico (entidades como unidad) + Prism en el "resto". Si el lenguaje
 * no se soporta o Prism falla, cada segmento de resto cae a texto plano escapado (y las entidades
 * se siguen realzando). Pensado para cargarse lazy desde CodeHighlight.
 */
export async function highlightToHtml(
  code: string,
  language: string | null | undefined,
): Promise<string> {
  const lang = resolveLanguage(language);
  let prism: PrismLike | null = null;
  let grammar: unknown = null;
  if (lang) {
    try {
      prism = await ensurePrism();
      await ensureLanguage(lang);
      grammar = prism.languages[lang] ?? null;
    } catch {
      prism = null; // degradación amable: el resto quedará como texto plano
      grammar = null;
    }
  }
  return splitBySemantic(code)
    .map((seg) => {
      if (seg.type === "sem") {
        return `<span class="${semClass(seg.kind ?? "", seg.text)}">${escapeHtml(seg.text)}</span>`;
      }
      if (prism && grammar && lang) {
        return prism.highlight(seg.text, grammar, lang);
      }
      return escapeHtml(seg.text);
    })
    .join("");
}
