// Detalle de un workspace (dentro del Sidebar): editar nombre, eliminar (owner), ver proyectos
// y gestión de miembros. Permisos como UX; errores por code vía i18n.

import { Button } from "primereact/button";
import { confirmDialog } from "primereact/confirmdialog";
import { InputText } from "primereact/inputtext";
import { Message } from "primereact/message";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { ApiError } from "../../../shared/api/errors";
import { PageLoader } from "../../../shared/ui/PageLoader";
import { ErrorState, InlineError } from "../../../shared/ui/states";
import { WorkspaceMembersSection } from "./WorkspaceMembersSection";
import { useDeleteWorkspace, useMyWorkspaceRole, useUpdateWorkspace, useWorkspace } from "../hooks";

export function WorkspaceDetailPanel({
  workspaceId,
  onClose,
}: {
  workspaceId: string;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const workspaceQuery = useWorkspace(workspaceId);
  const myRole = useMyWorkspaceRole(workspaceId);
  const update = useUpdateWorkspace(workspaceId);
  const remove = useDeleteWorkspace();

  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");

  const canEdit = myRole === "owner" || myRole === "admin";
  const canDelete = myRole === "owner";

  if (workspaceQuery.isLoading) return <PageLoader />;
  if (workspaceQuery.isError) {
    // Degradación amable para quien no puede gestionar el workspace (p. ej. guest): en vez del
    // error crudo, un mensaje con salida hacia "Mis proyectos".
    if (workspaceQuery.error instanceof ApiError && workspaceQuery.error.status === 403) {
      return (
        <div className="tf-detail">
          <Message severity="info" text={t("workspaces.noManageAccess")} />
          <div className="tf-detail-actions">
            <Button
              icon="pi pi-folder-open"
              label={t("workspaces.goToMyProjects")}
              onClick={() => {
                onClose();
                navigate("/projects");
              }}
            />
          </div>
        </div>
      );
    }
    return <ErrorState error={workspaceQuery.error} onRetry={() => workspaceQuery.refetch()} />;
  }
  const workspace = workspaceQuery.data;
  if (!workspace) return null;

  const startEdit = () => {
    setName(workspace.name);
    setEditing(true);
  };
  const saveName = () => update.mutate(name, { onSuccess: () => setEditing(false) });

  const confirmDelete = () => {
    confirmDialog({
      header: t("workspaces.deleteTitle"),
      message: t("workspaces.deleteConfirm", { name: workspace.name }),
      icon: "pi pi-exclamation-triangle",
      acceptLabel: t("common.delete"),
      rejectLabel: t("common.cancel"),
      acceptClassName: "p-button-danger",
      accept: () => remove.mutate(workspaceId, { onSuccess: onClose }),
    });
  };

  return (
    <div className="tf-detail">
      <div className="tf-detail-section">
        <h3>{t("workspaces.detailTitle")}</h3>
        {editing ? (
          <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
            <InputText
              value={name}
              onChange={(e) => setName(e.target.value)}
              style={{ flex: "1 1 200px" }}
              autoFocus
            />
            <Button
              icon="pi pi-check"
              label={t("common.save")}
              onClick={saveName}
              loading={update.isPending}
            />
            <Button
              icon="pi pi-times"
              text
              label={t("common.cancel")}
              onClick={() => setEditing(false)}
            />
          </div>
        ) : (
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
            <h2 className="tf-page-title" style={{ flex: 1 }}>
              {workspace.name}
            </h2>
            {canEdit ? (
              <Button
                text
                icon="pi pi-pencil"
                tooltip={t("workspaces.editName")}
                tooltipOptions={{ position: "bottom" }}
                onClick={startEdit}
              />
            ) : null}
          </div>
        )}
        {update.isError ? <InlineError error={update.error} /> : null}
      </div>

      <div className="tf-detail-actions">
        <Button
          icon="pi pi-folder-open"
          label={t("workspaces.viewProjects")}
          onClick={() => navigate(`/workspaces/${workspaceId}/projects`)}
        />
        {canDelete ? (
          <Button
            severity="danger"
            outlined
            icon="pi pi-trash"
            label={t("workspaces.deleteTitle")}
            onClick={confirmDelete}
            loading={remove.isPending}
          />
        ) : null}
      </div>
      {remove.isError ? <InlineError error={remove.error} /> : null}

      <div className="tf-detail-section">
        <h3>{t("members.title")}</h3>
        <WorkspaceMembersSection workspaceId={workspaceId} myRole={myRole} />
      </div>
    </div>
  );
}
