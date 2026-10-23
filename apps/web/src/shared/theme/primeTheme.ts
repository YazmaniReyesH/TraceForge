// Cablea PrimeReact a los tokens vía el preset **Lara teal** (claro/oscuro), intercambiando el
// stylesheet del tema al alternar. El "puente" de variables en tokens.css fuerza NUESTRA paleta
// (acento y superficies) sobre Lara, así no hay paleta divergente. Lara aporta el estilo de los
// componentes y la variante oscura correcta; nuestros tokens mandan en el color.

import laraDark from "primereact/resources/themes/lara-dark-teal/theme.css?url";
import laraLight from "primereact/resources/themes/lara-light-teal/theme.css?url";

import type { Theme } from "./themeStorage";

const LINK_ID = "tf-prime-theme";

export function applyPrimeReactTheme(theme: Theme): void {
  let link = document.getElementById(LINK_ID) as HTMLLinkElement | null;
  if (!link) {
    link = document.createElement("link");
    link.id = LINK_ID;
    link.rel = "stylesheet";
    document.head.appendChild(link);
  }
  link.href = theme === "dark" ? laraDark : laraLight;
}
