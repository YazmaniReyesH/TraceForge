// Barra de captura siempre accesible, en variante COMPACTA: en reposo solo los botones
// "+ Comando / + Nota"; al pulsar expande el formulario con ese tipo preseleccionado. Reduce el
// encimado sobre el timeline y mantiene la captura a un clic. Tras guardar sigue abierta (captura
// ágil en serie) y limpia el formulario; "Cancelar" la vuelve a plegar.

import { Button } from "primereact/button";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useAddItem } from "../hooks";
import type { EvidenceKind } from "../types";
import { EvidenceForm } from "./EvidenceForm";
import { emptyValues, toCreatePayload } from "./evidencePayload";

export function CaptureBar({
  workspaceId,
  projectId,
  sessionId,
  onAdded,
}: {
  workspaceId: string;
  projectId: string;
  sessionId: string;
  onAdded: (itemId: string) => void;
}) {
  const { t } = useTranslation();
  const add = useAddItem(workspaceId, projectId, sessionId);
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<EvidenceKind>("command");
  const [formKey, setFormKey] = useState(0);

  const start = (k: EvidenceKind) => {
    setKind(k);
    setOpen(true);
  };

  if (!open) {
    return (
      <div className="tf-capture tf-capture--collapsed">
        <span className="tf-capture__hint">{t("timeline.addBlock")}</span>
        <span className="tf-capture__spacer" />
        <Button
          outlined
          icon="pi pi-angle-right"
          label={t("timeline.command")}
          onClick={() => start("command")}
        />
        <Button
          outlined
          icon="pi pi-align-left"
          label={t("timeline.note")}
          onClick={() => start("note")}
        />
      </div>
    );
  }

  return (
    <div className="tf-capture">
      <EvidenceForm
        key={formKey}
        initial={emptyValues(kind)}
        submitLabel={t("timeline.add")}
        submitting={add.isPending}
        error={add.isError ? add.error : undefined}
        onCancel={() => setOpen(false)}
        onSubmit={(values) =>
          add.mutate(toCreatePayload(values), {
            onSuccess: (item) => {
              onAdded(item.evidence_item_id);
              setFormKey((k) => k + 1); // limpia el formulario y sigue abierta
            },
          })
        }
      />
    </div>
  );
}
