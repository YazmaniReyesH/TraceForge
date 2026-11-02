// Workspaces: lista (DataTable) + crear (dialog) + detalle en panel lateral (patrón lista+detalle).

import { Button } from "primereact/button";
import { Column } from "primereact/column";
import { DataTable, type DataTableRowClickEvent } from "primereact/datatable";
import { Dialog } from "primereact/dialog";
import { InputText } from "primereact/inputtext";
import { Sidebar } from "primereact/sidebar";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import { formatDateTime } from "../../../shared/i18n/format";
import { PageLoader } from "../../../shared/ui/PageLoader";
import { EmptyState, ErrorState, InlineError } from "../../../shared/ui/states";
import { WorkspaceDetailPanel } from "../components/WorkspaceDetailPanel";
import { useCreateWorkspace, useWorkspaces } from "../hooks";
import type { WorkspaceRead } from "../types";

export function WorkspacesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { workspaceId } = useParams();
  const list = useWorkspaces();
  const create = useCreateWorkspace();

  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");

  const onCreate = (e: FormEvent) => {
    e.preventDefault();
    create.mutate(
      { name: newName },
      {
        onSuccess: (ws) => {
          setShowCreate(false);
          setNewName("");
          navigate(`/workspaces/${ws.workspace_id}`);
        },
      },
    );
  };

  const createButton = (
    <Button icon="pi pi-plus" label={t("workspaces.create")} onClick={() => setShowCreate(true)} />
  );

  const body = () => {
    if (list.isLoading) return <PageLoader />;
    if (list.isError) return <ErrorState error={list.error} onRetry={() => list.refetch()} />;
    const workspaces = list.data ?? [];
    if (workspaces.length === 0) {
      return <EmptyState message={t("workspaces.empty")} action={createButton} />;
    }
    return (
      <DataTable
        value={workspaces}
        dataKey="workspace_id"
        selectionMode="single"
        onRowClick={(e: DataTableRowClickEvent) =>
          navigate(`/workspaces/${(e.data as WorkspaceRead).workspace_id}`)
        }
        removableSort
      >
        <Column field="name" header={t("common.name")} sortable />
        <Column
          header={t("workspaces.createdAt")}
          body={(w: WorkspaceRead) => formatDateTime(w.created_at)}
        />
      </DataTable>
    );
  };

  return (
    <div>
      <div className="tf-page-header">
        <div>
          <h1 className="tf-page-title">{t("workspaces.title")}</h1>
          <p className="tf-page-subtitle">{t("workspaces.subtitle")}</p>
        </div>
        {createButton}
      </div>

      {body()}

      <Sidebar
        visible={!!workspaceId}
        position="right"
        onHide={() => navigate("/workspaces")}
        style={{ width: "480px", maxWidth: "100vw" }}
      >
        {workspaceId ? (
          <WorkspaceDetailPanel workspaceId={workspaceId} onClose={() => navigate("/workspaces")} />
        ) : null}
      </Sidebar>

      <Dialog
        visible={showCreate}
        onHide={() => setShowCreate(false)}
        header={t("workspaces.createTitle")}
        style={{ width: "min(420px, 95vw)" }}
      >
        <form className="tf-stack" onSubmit={onCreate}>
          <InputText
            placeholder={t("workspaces.namePlaceholder")}
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
    </div>
  );
}
