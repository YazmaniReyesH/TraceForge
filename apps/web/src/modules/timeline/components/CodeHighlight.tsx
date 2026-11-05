// Render del comando: realce semántico SÍNCRONO al instante (entidades de seguridad) y, cuando el
// resaltador (Prism, lazy) termina, se sustituye por semántico + sintaxis. Colores por tokens.

import { useEffect, useState } from "react";

import { highlightToHtml, resolveLanguage } from "./highlight";
import { renderSemanticHtml } from "./semantic";

export function CodeHighlight({
  code,
  language,
}: {
  code: string;
  language: string | null | undefined;
}) {
  // Estado inicial: solo realce semántico (síncrono, sin bloquear ni esperar a Prism).
  const [html, setHtml] = useState(() => renderSemanticHtml(code));

  useEffect(() => {
    let active = true;
    setHtml(renderSemanticHtml(code)); // inmediato al cambiar el contenido
    if (resolveLanguage(language)) {
      void highlightToHtml(code, language).then((result) => {
        if (active) setHtml(result); // upgrade a semántico + sintaxis
      });
    }
    return () => {
      active = false;
    };
  }, [code, language]);

  return <code className="tf-code" dangerouslySetInnerHTML={{ __html: html }} />;
}
