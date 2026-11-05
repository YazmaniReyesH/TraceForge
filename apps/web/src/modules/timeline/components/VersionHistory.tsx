// Historial de versiones de un ítem (append-only): rastro completo con hash corto por versión.
// "Editar" ya crea una versión nueva en el backend; aquí solo se consulta el rastro.

import { Dialog } from "primereact/dialog";
import { useTranslation } from "react-i18next";

import { formatDateTime } from "../../../shared/i18n/format";
import { PageLoader } from "../../../shared/ui/PageLoader";
import { ErrorState } from "../../../shared/ui/states";
import { useItemDetail } from "../hooks";
import type { EvidenceItemVersionRead } from "../types";

function versionPreview(v: EvidenceItemVersionRead): string {
  if (v.note_text) return v.note_text;
  return [v.command_text, v.command_output].filter(Boolean).join("\n");
}

export function VersionHistory({
  workspaceId,
  projectId,
  sessionId,
  itemId,
  onHide,
}: {
  workspaceId: string;
  projectId: string;
  sessionId: string;
  itemId: string;
  onHide: () => void;
}) {
  const { t } = useTranslation();
  const detail = useItemDetail(workspaceId, projectId, sessionId, itemId);

  const body = () => {
    if (detail.isLoading) return <PageLoader />;
    if (detail.isError) return <ErrorState error={detail.error} onRetry={() => detail.refetch()} />;
    const data = detail.data;
    if (!data) return null;
    const versions = [...data.history].reverse(); // más reciente primero
    return (
      <ol className="tf-history">
        {versions.map((v) => (
          <li
            key={v.evidence_item_version_id}
            className={
              v.version === data.current_version
                ? "tf-history__item tf-history__item--current"
                : "tf-history__item"
            }
          >
            <div className="tf-history__meta">
              <span className="tf-history__ver">v{v.version}</span>
              {v.version === data.current_version ? (
                <span className="tf-history__badge">{t("timeline.currentVersion")}</span>
              ) : null}
              <span className="tf-history__spacer" />
              <span className="tf-telemetry__item" title={v.content_hash}>
                <i className="pi pi-hashtag" aria-hidden />
                <span className="tf-telemetry__hash">{v.content_hash.slice(0, 12)}</span>
              </span>
            </div>
            <div className="tf-history__date">{formatDateTime(v.captured_at)}</div>
            <pre className="tf-history__preview">{versionPreview(v)}</pre>
          </li>
        ))}
      </ol>
    );
  };

  return (
    <Dialog
      visible
      onHide={onHide}
      header={t("timeline.historyTitle")}
      style={{ width: "min(860px, 96vw)" }}
      contentStyle={{ maxHeight: "72vh" }}
    >
      {body()}
    </Dialog>
  );
}
