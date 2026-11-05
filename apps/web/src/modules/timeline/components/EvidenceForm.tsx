// Formulario reutilizable de evidencia (captura y edición). El contenedor decide el chrome
// (barra sticky o diálogo). Construye el payload EvidenceItemCreate según el kind.

import { Button } from "primereact/button";
import { InputText } from "primereact/inputtext";
import { InputTextarea } from "primereact/inputtextarea";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { InlineError } from "../../../shared/ui/states";
import type { EvidenceKind } from "../types";
import { type EvidenceFormValues } from "./evidencePayload";

export function EvidenceForm({
  initial,
  kindLocked = false,
  submitting = false,
  submitLabel,
  error,
  onSubmit,
  onCancel,
}: {
  initial: EvidenceFormValues;
  kindLocked?: boolean;
  submitting?: boolean;
  submitLabel: string;
  error?: unknown;
  onSubmit: (values: EvidenceFormValues) => void;
  onCancel?: () => void;
}) {
  const { t } = useTranslation();
  const [v, setV] = useState<EvidenceFormValues>(initial);
  const [showAdvanced, setShowAdvanced] = useState(
    !!(initial.command_output || initial.tool || initial.language),
  );

  const set = <K extends keyof EvidenceFormValues>(key: K, value: EvidenceFormValues[K]) =>
    setV((prev) => ({ ...prev, [key]: value }));

  const valid =
    v.kind === "command" ? v.command_text.trim().length > 0 : v.note_text.trim().length > 0;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (valid && !submitting) onSubmit(v);
  };

  const kindButton = (kind: EvidenceKind, icon: string, label: string) => (
    <button
      type="button"
      className={v.kind === kind ? "tf-capture__kind tf-capture__kind--active" : "tf-capture__kind"}
      onClick={() => set("kind", kind)}
      disabled={kindLocked && v.kind !== kind}
      aria-pressed={v.kind === kind}
    >
      <i className={icon} aria-hidden />
      {label}
    </button>
  );

  return (
    <form className="tf-capture__row" onSubmit={submit}>
      {!kindLocked ? (
        <div className="tf-capture__kinds" role="group" aria-label={t("timeline.kind")}>
          {kindButton("command", "pi pi-angle-right", t("timeline.command"))}
          {kindButton("note", "pi pi-align-left", t("timeline.note"))}
        </div>
      ) : null}

      {v.kind === "command" ? (
        <>
          <InputText
            className="tf-mono-input"
            placeholder={t("timeline.commandPlaceholder")}
            value={v.command_text}
            onChange={(e) => set("command_text", e.target.value)}
            autoFocus
          />
          {showAdvanced ? (
            <>
              <InputTextarea
                className="tf-mono-input"
                placeholder={t("timeline.outputPlaceholder")}
                value={v.command_output}
                onChange={(e) => set("command_output", e.target.value)}
                rows={4}
                autoResize
              />
              <div className="tf-capture__inline">
                <InputText
                  placeholder={t("timeline.toolPlaceholder")}
                  value={v.tool}
                  onChange={(e) => set("tool", e.target.value)}
                />
                <InputText
                  placeholder={t("timeline.languagePlaceholder")}
                  value={v.language}
                  onChange={(e) => set("language", e.target.value)}
                />
              </div>
            </>
          ) : (
            <button
              type="button"
              className="tf-cmd__toggle"
              style={{ margin: 0 }}
              onClick={() => setShowAdvanced(true)}
            >
              <i className="pi pi-plus" aria-hidden />
              {t("timeline.addOutput")}
            </button>
          )}
        </>
      ) : (
        <InputTextarea
          placeholder={t("timeline.notePlaceholder")}
          value={v.note_text}
          onChange={(e) => set("note_text", e.target.value)}
          rows={3}
          autoResize
          autoFocus
        />
      )}

      {error ? <InlineError error={error} /> : null}

      <div className="tf-capture__footer">
        <span />
        <div style={{ display: "flex", gap: "var(--space-2)" }}>
          {onCancel ? (
            <Button type="button" text label={t("common.cancel")} onClick={onCancel} />
          ) : null}
          <Button
            type="submit"
            icon="pi pi-plus"
            label={submitLabel}
            loading={submitting}
            disabled={!valid}
          />
        </div>
      </div>
    </form>
  );
}
