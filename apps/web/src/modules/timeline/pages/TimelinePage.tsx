// Pantalla de timeline dentro de un project: lista de sesiones + timeline de la sesión activa.

import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";

import { PageLoader } from "../../../shared/ui/PageLoader";
import { EmptyState, ErrorState } from "../../../shared/ui/states";
import { useMyEffectiveProjectRole, useProject } from "../../projects/hooks";
import { SessionList } from "../components/SessionList";
import { TimelineView } from "../components/TimelineView";
import { useSessions } from "../hooks";
import "../timeline.css";

export function TimelinePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const params = useParams();
  const workspaceId = params.workspaceId as string;
  const projectId = params.projectId as string;
  const sessionId = params.sessionId;

  const project = useProject(workspaceId, projectId);
  const role = useMyEffectiveProjectRole(workspaceId, projectId);
  const sessions = useSessions(workspaceId, projectId);
  const canWrite = role === "lead" || role === "contributor";

  const timelineBase = `/workspaces/${workspaceId}/projects/${projectId}/timeline`;
  const selectSession = (sid: string) => navigate(`${timelineBase}/${sid}`);

  // Auto-selecciona la primera sesión si no hay ninguna activa (y existe al menos una).
  const firstSessionId = sessions.data?.[0]?.session_id;
  useEffect(() => {
    if (!sessionId && firstSessionId) {
      navigate(`${timelineBase}/${firstSessionId}`, { replace: true });
    }
  }, [sessionId, firstSessionId, timelineBase, navigate]);

  if (project.isLoading) return <PageLoader />;
  if (project.isError) return <ErrorState error={project.error} />;

  return (
    <div className="tf-tl-page">
      <nav className="tf-breadcrumb">
        <Link to="/workspaces">{t("projects.backToWorkspaces")}</Link>
        <span>/</span>
        <Link to={`/workspaces/${workspaceId}/projects/${projectId}`}>
          {project.data?.name ?? t("projects.title")}
        </Link>
        <span>/</span>
        <span>{t("timeline.title")}</span>
      </nav>

      <div className="tf-page-header">
        <div>
          <h1 className="tf-page-title">{t("timeline.title")}</h1>
          <p className="tf-page-subtitle">{t("timeline.subtitle")}</p>
        </div>
      </div>

      <div className="tf-tl-layout">
        <SessionList
          workspaceId={workspaceId}
          projectId={projectId}
          activeSessionId={sessionId}
          canWrite={canWrite}
          onSelect={selectSession}
          onCleared={() => navigate(timelineBase, { replace: true })}
        />
        <div className="tf-tl-main">
          {sessionId ? (
            <TimelineView
              workspaceId={workspaceId}
              projectId={projectId}
              sessionId={sessionId}
              canWrite={canWrite}
            />
          ) : (
            <EmptyState message={t("timeline.pickSession")} />
          )}
        </div>
      </div>
    </div>
  );
}
