// Detalle de un proyecto (Sidebar): editar nombre (lead/contributor), eliminar (lead),
// y gestión de miembros (lead). classification/ai_policy están reservados (solo lectura).

import { Button } from "primereact/button";
import { confirmDialog } from "primereact/confirmdialog";
import { InputText } from "primereact/inputtext";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { PageLoader } from "../../../shared/ui/PageLoader";
import { ErrorState, InlineError } from "../../../shared/ui/states";
import { ProjectMembersSection } from "./ProjectMembersSection";
import {
  useDeleteProject,
  useMyEffectiveProjectRole,
  useProject,
  useUpdateProject,
} from "../hooks";

export function ProjectDetailPanel({
  workspaceId,
  projectId,
  onClose,
}: {
  workspaceId: string;
  projectId: string;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const projectQuery = useProject(workspaceId, projectId);
  const effectiveRole = useMyEffectiveProjectRole(workspaceId, projectId);
  const update = useUpdateProject(workspaceId, projectId);
  const remove = useDeleteProject(workspaceId);

  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");

  const canEdit = effectiveRole === "lead" || effectiveRole === "contributor";
  const canDelete = effectiveRole === "lead";
  const canManageMembers = effectiveRole === "lead";

  if (projectQuery.isLoading) return <PageLoader />;
  if (projectQuery.isError)
    return <ErrorState error={projectQuery.error} onRetry={() => projectQuery.refetch()} />;
  const project = projectQuery.data;
  if (!project) return null;

  const startEdit = () => {
    setName(project.name);
    setEditing(true);
  };
  const saveName = () => update.mutate(name, { onSuccess: () => setEditing(false) });

  const confirmDelete = () => {
    confirmDialog({
      header: t("projects.deleteTitle"),
      message: t("projects.deleteConfirm", { name: project.name }),
      icon: "pi pi-exclamation-triangle",
      acceptLabel: t("common.delete"),
      rejectLabel: t("common.cancel"),
      acceptClassName: "p-button-danger",
      accept: () => remove.mutate(projectId, { onSuccess: onClose }),
    });
  };

  return (
    <div className="tf-detail">
      <div className="tf-detail-section">
        <h3>{t("projects.detailTitle")}</h3>
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
              {project.name}
            </h2>
            {canEdit ? (
              <Button
                text
                icon="pi pi-pencil"
                tooltip={t("common.edit")}
                tooltipOptions={{ position: "bottom" }}
                onClick={startEdit}
              />
            ) : null}
          </div>
        )}
        {update.isError ? <InlineError error={update.error} /> : null}
        <p className="tf-member-sub">
          {t("projects.classification")}:{" "}
          {project.classification ?? t("projects.classificationReserved")}
        </p>
      </div>

      {canDelete ? (
        <div className="tf-detail-actions">
          <Button
            severity="danger"
            outlined
            icon="pi pi-trash"
            label={t("projects.deleteTitle")}
            onClick={confirmDelete}
            loading={remove.isPending}
          />
        </div>
      ) : null}
      {remove.isError ? <InlineError error={remove.error} /> : null}

      <div className="tf-detail-section">
        <h3>{t("members.title")}</h3>
        <ProjectMembersSection
          workspaceId={workspaceId}
          projectId={projectId}
          canManage={canManageMembers}
        />
      </div>
    </div>
  );
}
