// Nota: identidad propia (tipografía Inter, acento lateral distinto del comando, icono) + copiar.

import { useTranslation } from "react-i18next";

import type { EvidenceItemVersionRead } from "../types";
import { CopyButton } from "./CopyButton";

export function NoteBlock({ version }: { version: EvidenceItemVersionRead }) {
  const { t } = useTranslation();
  return (
    <div className="tf-note">
      <i className="pi pi-align-left tf-note__icon" aria-hidden />
      <p className="tf-note__text">{version.note_text}</p>
      <CopyButton text={version.note_text ?? ""} label={t("timeline.copyNote")} />
    </div>
  );
}
