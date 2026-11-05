// Lista/selector de sesiones de la sesión activa: crear, renombrar y soft-delete (con confirmación).

import { Button } from "primereact/button";
import { confirmDialog } from "primereact/confirmdialog";
import { Dialog } from "primereact/dialog";
import { InputText } from "primereact/inputtext";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { PageLoader } from "../../../shared/ui/PageLoader";
import { EmptyState, ErrorState, InlineError } from "../../../shared/ui/states";
import { useCreateSession, useDeleteSession, useRenameSession, useSessions } from "../hooks";
import type { SessionRead } from "../types";

export function SessionList({
  workspaceId,
  projectId,
  activeSessionId,
  canWrite,
  onSelect,
  onCleared,
}: {
  workspaceId: string;
  projectId: string;
  activeSessionId: string | undefined;
  canWrite: boolean;
  onSelect: (sessionId: string) => void;
  onCleared: () => void;
}) {
  const { t } = useTranslation();
  const list = useSessions(workspaceId, projectId);
  const create = useCreateSession(workspaceId, projectId);
  const rename = useRenameSession(workspaceId, projectId);
  const remove = useDeleteSession(workspaceId, projectId);

  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [renaming, setRenaming] = useState<SessionRead | null>(null);
  const [renameName, setRenameName] = useState("");

  const onCreate = (e: FormEvent) => {
    e.preventDefault();
    create.mutate(
      { name: newName },
      {
        onSuccess: (s) => {
          setShowCreate(false);
          setNewName("");
          onSelect(s.session_id);
        },
      },
    );
  };

  const onRename = (e: FormEvent) => {
    e.preventDefault();
    if (!renaming) return;
    rename.mutate(
      { sid: renaming.session_id, name: renameName },
      { onSuccess: () => setRenaming(null) },
    );
  };

  const confirmDelete = (s: SessionRead) => {
    // Vecino al que reposicionar si borramos la sesión activa: la anterior, si no la siguiente.
    const all = list.data ?? [];
    const idx = all.findIndex((x) => x.session_id === s.session_id);
    const neighbor = all[idx - 1] ?? all[idx + 1];
    confirmDialog({
      header: t("timeline.deleteSessionTitle"),
      message: t("timeline.deleteSessionConfirm", { name: s.name }),
      icon: "pi pi-exclamation-triangle",
      acceptLabel: t("common.delete"),
      rejectLabel: t("common.cancel"),
      acceptClassName: "p-button-danger",
      accept: () =>
        remove.mutate(s.session_id, {
          onSuccess: () => {
            // Evita dejar a la vista una sesión que ya no existe ("fantasma").
            if (s.session_id === activeSessionId) {
              if (neighbor) onSelect(neighbor.session_id);
              else onCleared();
            }
          },
        }),
    });
  };

  return (
    <aside className="tf-sessions">
      <div className="tf-sessions-head">
        <h2>{t("timeline.sessions")}</h2>
        {canWrite ? (
          <Button
            text
            rounded
            icon="pi pi-plus"
            aria-label={t("timeline.newSession")}
            tooltip={t("timeline.newSession")}
            tooltipOptions={{ position: "bottom" }}
            onClick={() => setShowCreate(true)}
          />
        ) : null}
      </div>

      {list.isLoading ? <PageLoader /> : null}
      {list.isError ? <ErrorState error={list.error} onRetry={() => list.refetch()} /> : null}
      {list.data && list.data.length === 0 ? (
        <EmptyState message={t("timeline.noSessions")} />
      ) : null}

      {(list.data ?? []).map((s) => (
        <div
          key={s.session_id}
          className={
            s.session_id === activeSessionId
              ? "tf-session-item tf-session-item--active"
              : "tf-session-item"
          }
        >
          <button
            type="button"
            className="tf-session-item__btn"
            title={s.name}
            onClick={() => onSelect(s.session_id)}
          >
            {s.name}
          </button>
          {canWrite ? (
            <span className="tf-session-actions">
              <Button
                text
                rounded
                icon="pi pi-pencil"
                aria-label={t("timeline.renameSession")}
                onClick={() => {
                  setRenaming(s);
                  setRenameName(s.name);
                }}
              />
              <Button
                text
                rounded
                severity="danger"
                icon="pi pi-trash"
                aria-label={t("timeline.deleteSessionTitle")}
                onClick={() => confirmDelete(s)}
              />
            </span>
          ) : null}
        </div>
      ))}

      <Dialog
        visible={showCreate}
        onHide={() => setShowCreate(false)}
        header={t("timeline.newSession")}
        style={{ width: "min(420px, 95vw)" }}
      >
        <form className="tf-stack" onSubmit={onCreate}>
          <InputText
            placeholder={t("timeline.sessionNamePlaceholder")}
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            autoFocus
            required
          />
          {create.isError ? <InlineError error={create.error} /> : null}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "var(--space-2)" }}>
            <Button
              type="button"
              text
              label={t("common.cancel")}
              onClick={() => setShowCreate(false)}
            />
            <Button type="submit" label={t("common.create")} loading={create.isPending} />
          </div>
        </form>
      </Dialog>

      <Dialog
        visible={!!renaming}
        onHide={() => setRenaming(null)}
        header={t("timeline.renameSession")}
        style={{ width: "min(420px, 95vw)" }}
      >
        <form className="tf-stack" onSubmit={onRename}>
          <InputText
            value={renameName}
            onChange={(e) => setRenameName(e.target.value)}
            autoFocus
            required
          />
          {rename.isError ? <InlineError error={rename.error} /> : null}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "var(--space-2)" }}>
            <Button
              type="button"
              text
              label={t("common.cancel")}
              onClick={() => setRenaming(null)}
            />
            <Button type="submit" label={t("common.save")} loading={rename.isPending} />
          </div>
        </form>
      </Dialog>
    </aside>
  );
}
