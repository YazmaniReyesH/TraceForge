// Un nodo del timeline: punto en el riel + tarjeta (comando/nota) + telemetría (hora, hash corto,
// versión, "editado · ver historial") + acciones (arrastrar/editar/borrar) si hay permiso.

import { Button } from "primereact/button";
import type { DragEvent } from "react";
import { useTranslation } from "react-i18next";

import { formatDateTime } from "../../../shared/i18n/format";
import type { EvidenceItemRead } from "../types";
import { CommandBlock } from "./CommandBlock";
import { NoteBlock } from "./NoteBlock";

export interface NodeDragHandlers {
  draggingId: string | null;
  dropHint: { overId: string; half: "before" | "after" } | null;
  onDragStart: (id: string) => void;
  onDragOver: (e: DragEvent, id: string) => void;
  onDrop: (id: string) => void;
  onDragEnd: () => void;
}

export function EvidenceNode({
  item,
  isActive,
  isNew,
  canWrite,
  drag,
  onEdit,
  onDelete,
  onShowHistory,
}: {
  item: EvidenceItemRead;
  isActive: boolean;
  isNew: boolean;
  canWrite: boolean;
  drag: NodeDragHandlers;
  onEdit: (item: EvidenceItemRead) => void;
  onDelete: (item: EvidenceItemRead) => void;
  onShowHistory: (itemId: string) => void;
}) {
  const { t } = useTranslation();
  const id = item.evidence_item_id;
  const shortHash = item.current.content_hash.slice(0, 12);

  const hint = drag.dropHint?.overId === id ? drag.dropHint.half : null;
  const classes = [
    "tf-node",
    isActive ? "tf-node--active" : "",
    isNew ? "tf-node--new" : "",
    drag.draggingId === id ? "tf-node--dragging" : "",
    hint === "before" ? "tf-node--drop-before" : "",
    hint === "after" ? "tf-node--drop-after" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      className={classes}
      draggable={canWrite}
      onDragStart={() => drag.onDragStart(id)}
      onDragOver={(e) => drag.onDragOver(e, id)}
      onDrop={() => drag.onDrop(id)}
      onDragEnd={drag.onDragEnd}
    >
      <span className="tf-node__dot" aria-hidden />
      <div className="tf-node__card">
        {item.kind === "command" ? (
          <CommandBlock version={item.current} />
        ) : (
          <NoteBlock version={item.current} />
        )}

        <div className="tf-telemetry">
          <span className="tf-telemetry__item">
            <i className="pi pi-clock" aria-hidden /> {formatDateTime(item.current.captured_at)}
          </span>
          <span className="tf-telemetry__item" title={item.current.content_hash}>
            <i className="pi pi-hashtag" aria-hidden />
            <span className="tf-telemetry__hash">{shortHash}</span>
          </span>
          <span className="tf-telemetry__item">v{item.current_version}</span>
          {item.current_version > 1 ? (
            <button
              type="button"
              className="tf-telemetry__edited"
              onClick={() => onShowHistory(id)}
            >
              <i className="pi pi-history" aria-hidden /> {t("timeline.editedHistory")}
            </button>
          ) : null}

          <span className="tf-telemetry__spacer" />

          {canWrite ? (
            <span className="tf-node__actions">
              <button
                type="button"
                className="tf-drag-handle"
                aria-label={t("timeline.dragHint")}
                title={t("timeline.dragHint")}
              >
                <i className="pi pi-bars" aria-hidden />
              </button>
              <Button
                text
                rounded
                icon="pi pi-pencil"
                aria-label={t("common.edit")}
                tooltip={t("timeline.editNewVersion")}
                tooltipOptions={{ position: "bottom" }}
                onClick={() => onEdit(item)}
              />
              <Button
                text
                rounded
                severity="danger"
                icon="pi pi-trash"
                aria-label={t("common.delete")}
                onClick={() => onDelete(item)}
              />
            </span>
          ) : null}
        </div>
      </div>
    </div>
  );
}
