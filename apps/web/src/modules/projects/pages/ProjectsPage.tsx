// Projects dentro de un workspace: lista + crear (owner/admin) + detalle en panel lateral.

import { Button } from "primereact/button";
import { Column } from "primereact/column";
import { DataTable, type DataTableRowClickEvent } from "primereact/datatable";
import { Dialog } from "primereact/dialog";
import { InputText } from "primereact/inputtext";
import { Sidebar } from "primereact/sidebar";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";

import { formatDateTime } from "../../../shared/i18n/format";
import { PageLoader } from "../../../shared/ui/PageLoader";
import { EmptyState, ErrorState, InlineError } from "../../../shared/ui/states";
import { useMyWorkspaceRole, useWorkspace } from "../../workspaces/hooks";
import { ProjectDetailPanel } from "../components/ProjectDetailPanel";
import { useCreateProject, useProjects } from "../hooks";
import type { ProjectRead } from "../types";

export function ProjectsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const params = useParams();
  const workspaceId = params.workspaceId as string;
  const projectId = params.projectId;

  const workspace = useWorkspace(workspaceId);
  const myWsRole = useMyWorkspaceRole(workspaceId);
  const list = useProjects(workspaceId);
  const create = useCreateProject(workspaceId);

  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");

  const canCreate = myWsRole === "owner" || myWsRole === "admin";

  const onCreate = (e: FormEvent) => {
    e.preventDefault();
    create.mutate(
      { name: newName },
      {
        onSuccess: (p) => {
          setShowCreate(false);
          setNewName("");
          navigate(`/workspaces/${workspaceId}/projects/${p.project_id}`);
        },
      },
    );
  };

  const createButton = canCreate ? (
    <Button icon="pi pi-plus" label={t("projects.create")} onClick={() => setShowCreate(true)} />
  ) : null;

  const body = () => {
    if (list.isLoading) return <PageLoader />;
    if (list.isError) return <ErrorState error={list.error} onRetry={() => list.refetch()} />;
    const projects = list.data ?? [];
    if (projects.length === 0) {
      return <EmptyState message={t("projects.empty")} action={createButton ?? undefined} />;
    }
    return (
      <DataTable
        value={projects}
        dataKey="project_id"
        selectionMode="single"
        onRowClick={(e: DataTableRowClickEvent) =>
          navigate(`/workspaces/${workspaceId}/projects/${(e.data as ProjectRead).project_id}`)
        }
        removableSort
      >
        <Column field="name" header={t("common.name")} sortable />
        <Column
          header={t("workspaces.createdAt")}
          body={(p: ProjectRead) => formatDateTime(p.created_at)}
        />
      </DataTable>
    );
  };

  return (
    <div>
      <nav className="tf-breadcrumb">
        <Link to="/workspaces">{t("projects.backToWorkspaces")}</Link>
        <span>/</span>
        <span>{workspace.data?.name ?? t("projects.title")}</span>
      </nav>

      <div className="tf-page-header">
        <h1 className="tf-page-title">{t("projects.title")}</h1>
        {createButton}
      </div>

      {body()}

      <Sidebar
        visible={!!projectId}
        position="right"
        onHide={() => navigate(`/workspaces/${workspaceId}/projects`)}
        style={{ width: "480px", maxWidth: "100vw" }}
      >
        {projectId ? (
          <ProjectDetailPanel
            workspaceId={workspaceId}
            projectId={projectId}
            onClose={() => navigate(`/workspaces/${workspaceId}/projects`)}
          />
        ) : null}
      </Sidebar>

      <Dialog
        visible={showCreate}
        onHide={() => setShowCreate(false)}
        header={t("projects.createTitle")}
        style={{ width: "min(420px, 95vw)" }}
      >
        <form className="tf-stack" onSubmit={onCreate}>
          <InputText
            placeholder={t("projects.namePlaceholder")}
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
