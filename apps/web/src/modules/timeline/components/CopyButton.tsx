// Botón "copiar" con feedback breve de "copiado". Aparece en hover/focus del nodo (ver CSS).

import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

export function CopyButton({ text, label }: { text: string; label?: string }) {
  const { t } = useTranslation();
  const [done, setDone] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setDone(false), 1500);
    } catch {
      // Sin acceso al portapapeles: no hacemos nada ruidoso.
    }
  };

  return (
    <button
      type="button"
      className={done ? "tf-copy tf-copy--done" : "tf-copy"}
      onClick={() => void onCopy()}
      aria-label={label ?? t("timeline.copy")}
    >
      <i className={done ? "pi pi-check" : "pi pi-copy"} aria-hidden />
      <span>{done ? t("timeline.copied") : t("timeline.copy")}</span>
    </button>
  );
}
