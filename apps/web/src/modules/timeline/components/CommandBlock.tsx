// Bloque de comando tratado como terminal: cabecera (tool/language) + prompt $ + comando
// resaltado (lazy) + salida distinguible y colapsable + copiar en hover.

import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { EvidenceItemVersionRead } from "../types";
import { CodeHighlight } from "./CodeHighlight";
import { CopyButton } from "./CopyButton";
import { renderSemanticHtml } from "./semantic";

// Umbral para colapsar outputs largos (caracteres o líneas).
const LONG_CHARS = 400;
const LONG_LINES = 8;

export function CommandBlock({ version }: { version: EvidenceItemVersionRead }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  const command = version.command_text ?? "";
  const output = version.command_output ?? "";
  const hasOutput = output.trim().length > 0;
  const long = output.length > LONG_CHARS || output.split("\n").length > LONG_LINES;
  const clamped = long && !expanded;

  return (
    <div className="tf-cmd">
      <div className="tf-cmd__head">
        <span className="tf-cmd__tool">{version.tool || t("timeline.command")}</span>
        {version.language ? <span>· {version.language}</span> : null}
        <span className="tf-cmd__spacer" />
        <CopyButton text={command} label={t("timeline.copyCommand")} />
      </div>
      <div className="tf-cmd__body">
        <span className="tf-cmd__prompt" aria-hidden>
          $
        </span>
        <CodeHighlight code={command} language={version.language ?? "bash"} />
      </div>
      {hasOutput ? (
        <>
          <div className="tf-cmd__outhead">
            <span className="tf-cmd__outlabel">{t("timeline.output")}</span>
            <span className="tf-cmd__spacer" />
            <CopyButton text={output} label={t("timeline.copyOutput")} />
          </div>
          <pre
            className={clamped ? "tf-cmd__output tf-cmd__output--clamped" : "tf-cmd__output"}
            dangerouslySetInnerHTML={{ __html: renderSemanticHtml(output) }}
          />
          {long ? (
            <button
              type="button"
              className="tf-cmd__toggle"
              onClick={() => setExpanded((v) => !v)}
              aria-expanded={expanded}
            >
              <i className={expanded ? "pi pi-chevron-up" : "pi pi-chevron-down"} aria-hidden />
              {expanded ? t("timeline.showLess") : t("timeline.showMore")}
            </button>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
