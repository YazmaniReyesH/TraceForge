// "Mis proyectos": vista transversal (todos los workspaces). El nombre del workspace va como
// columna de contexto (la lista mezcla proyectos de distintos workspaces). Cada fila abre el
// detalle del project existente, que ya funciona para un guest viewer.

import { Column } from "primereact/column";
import { DataTable, type DataTableRowClickEvent } from "primereact/datatable";
import { Tag } from "primereact/tag";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { PageLoader } from "../../../shared/ui/PageLoader";
import { EmptyState, ErrorState } from "../../../shared/ui/states";
import { useMyProjects } from "../hooks";
import type { MyProjectRead } from "../types";

export function MyProjectsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const list = useMyProjects();

  const body = () => {
    if (list.isLoading) return <PageLoader />;
    if (list.isError) return <ErrorState error={list.error} onRetry={() => list.refetch()} />;
    const projects = list.data ?? [];
    if (projects.length === 0) return <EmptyState message={t("myProjects.empty")} />;
    return (
      <DataTable
        value={projects}
        dataKey="project_id"
        selectionMode="single"
        onRowClick={(e: DataTableRowClickEvent) => {
          const p = e.data as MyProjectRead;
          navigate(`/workspaces/${p.workspace_id}/projects/${p.project_id}`);
        }}
        removableSort
      >
        <Column field="name" header={t("myProjects.colProject")} sortable />
        <Column field="workspace_name" header={t("myProjects.colWorkspace")} sortable />
        <Column
          header={t("myProjects.colRole")}
          body={(p: MyProjectRead) => <Tag value={t(`roles.project.${p.role}`)} />}
        />
      </DataTable>
    );
  };

  return (
    <div>
      <div className="tf-page-header">
        <div>
          <h1 className="tf-page-title">{t("myProjects.title")}</h1>
          <p className="tf-page-subtitle">{t("myProjects.subtitle")}</p>
        </div>
      </div>
      {body()}
    </div>
  );
}
