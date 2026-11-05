// Vista de timeline de la sesión activa: riel + nodos ordenados, captura, reordenar por arrastre
// (optimista), edición (versión nueva), historial y borrado. Estados de carga/error/vacío.

import { confirmDialog } from "primereact/confirmdialog";
import { Dialog } from "primereact/dialog";
import { type DragEvent, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { EmptyState, ErrorState, InlineError } from "../../../shared/ui/states";
import { useDeleteItem, useEditItem, useItems, useMoveItem } from "../hooks";
import type { EvidenceItemRead } from "../types";
import { CaptureBar } from "./CaptureBar";
import { EvidenceForm } from "./EvidenceForm";
import { type EvidenceFormValues, toCreatePayload } from "./evidencePayload";
import { EvidenceNode, type NodeDragHandlers } from "./EvidenceNode";
import { VersionHistory } from "./VersionHistory";

function TimelineSkeleton() {
  return (
    <div className="tf-rail" aria-hidden>
      {[0, 1, 2].map((i) => (
        <div key={i} className="tf-node">
          <span className="tf-node__dot" />
          <div className="tf-node__card">
            <div className="tf-skel" style={{ height: "2.5rem" }} />
            <div className="tf-skel" style={{ height: "1.5rem" }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function editInitial(item: EvidenceItemRead): EvidenceFormValues {
  const v = item.current;
  return {
    kind: item.kind,
    command_text: v.command_text ?? "",
    command_output: v.command_output ?? "",
    tool: v.tool ?? "",
    language: v.language ?? "",
    note_text: v.note_text ?? "",
  };
}

export function TimelineView({
  workspaceId,
  projectId,
  sessionId,
  canWrite,
}: {
  workspaceId: string;
  projectId: string;
  sessionId: string;
  canWrite: boolean;
}) {
  const { t } = useTranslation();
  const items = useItems(workspaceId, projectId, sessionId);
  const move = useMoveItem(workspaceId, projectId, sessionId);
  const remove = useDeleteItem(workspaceId, projectId, sessionId);
  const edit = useEditItem(workspaceId, projectId, sessionId);

  const [newId, setNewId] = useState<string | null>(null);
  const [editing, setEditing] = useState<EvidenceItemRead | null>(null);
  const [historyId, setHistoryId] = useState<string | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dropHint, setDropHint] = useState<{ overId: string; half: "before" | "after" } | null>(
    null,
  );
  const scanTimer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(scanTimer.current), []);

  const onAdded = (itemId: string) => {
    setNewId(itemId);
    window.clearTimeout(scanTimer.current);
    scanTimer.current = window.setTimeout(() => setNewId(null), 600);
  };

  const list = items.data ?? [];

  const drag: NodeDragHandlers = {
    draggingId,
    dropHint,
    onDragStart: (id) => setDraggingId(id),
    onDragOver: (e: DragEvent, id) => {
      if (!draggingId || id === draggingId) return;
      e.preventDefault();
      const rect = e.currentTarget.getBoundingClientRect();
      const half = e.clientY - rect.top < rect.height / 2 ? "before" : "after";
      setDropHint((prev) =>
        prev?.overId === id && prev.half === half ? prev : { overId: id, half },
      );
    },
    onDrop: (targetId) => {
      const dragId = draggingId;
      const hint = dropHint;
      setDraggingId(null);
      setDropHint(null);
      if (!dragId || dragId === targetId || !hint) return;
      const idx = list.findIndex((i) => i.evidence_item_id === targetId);
      if (idx < 0) return;
      const afterId = hint.half === "after" ? targetId : (list[idx - 1]?.evidence_item_id ?? null); // "before" → después del anterior (o al inicio)
      if (afterId === dragId) return; // no-op
      move.mutate({ itemId: dragId, afterItemId: afterId });
    },
    onDragEnd: () => {
      setDraggingId(null);
      setDropHint(null);
    },
  };

  const confirmDelete = (item: EvidenceItemRead) =>
    confirmDialog({
      header: t("timeline.deleteItemTitle"),
      message: t("timeline.deleteItemConfirm"),
      icon: "pi pi-exclamation-triangle",
      acceptLabel: t("common.delete"),
      rejectLabel: t("common.cancel"),
      acceptClassName: "p-button-danger",
      accept: () => remove.mutate(item.evidence_item_id),
    });

  if (items.isLoading) return <TimelineSkeleton />;
  if (items.isError) return <ErrorState error={items.error} onRetry={() => items.refetch()} />;

  return (
    <div>
      {move.isError ? <InlineError error={move.error} /> : null}
      {remove.isError ? <InlineError error={remove.error} /> : null}

      {list.length === 0 ? (
        <EmptyState message={t("timeline.noItems")} />
      ) : (
        <div className="tf-rail">
          {list.map((item, idx) => (
            <EvidenceNode
              key={item.evidence_item_id}
              item={item}
              isActive={idx === list.length - 1}
              isNew={item.evidence_item_id === newId}
              canWrite={canWrite}
              drag={drag}
              onEdit={setEditing}
              onDelete={confirmDelete}
              onShowHistory={setHistoryId}
            />
          ))}
        </div>
      )}

      {canWrite ? (
        <CaptureBar
          workspaceId={workspaceId}
          projectId={projectId}
          sessionId={sessionId}
          onAdded={onAdded}
        />
      ) : null}

      <Dialog
        visible={!!editing}
        onHide={() => setEditing(null)}
        header={t("timeline.editItemTitle")}
        style={{ width: "min(560px, 95vw)" }}
      >
        {editing ? (
          <EvidenceForm
            initial={editInitial(editing)}
            kindLocked
            submitLabel={t("common.save")}
            submitting={edit.isPending}
            error={edit.isError ? edit.error : undefined}
            onSubmit={(values) =>
              edit.mutate(
                { itemId: editing.evidence_item_id, body: toCreatePayload(values) },
                { onSuccess: () => setEditing(null) },
              )
            }
            onCancel={() => setEditing(null)}
          />
        ) : null}
      </Dialog>

      {historyId ? (
        <VersionHistory
          workspaceId={workspaceId}
          projectId={projectId}
          sessionId={sessionId}
          itemId={historyId}
          onHide={() => setHistoryId(null)}
        />
      ) : null}
    </div>
  );
}
