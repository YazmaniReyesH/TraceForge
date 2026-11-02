// Estados reutilizables de lista/pantalla: vacío y error. (Carga: PageLoader.)

import { Button } from "primereact/button";
import { Message } from "primereact/message";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { apiErrorMessage } from "../api/errors";

export function EmptyState({ message, action }: { message: string; action?: ReactNode }) {
  return (
    <div
      style={{
        padding: "var(--space-6)",
        textAlign: "center",
        color: "var(--text-muted)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-3)",
        alignItems: "center",
      }}
    >
      <i className="pi pi-inbox" style={{ fontSize: "1.5rem" }} aria-hidden />
      <span>{message}</span>
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useTranslation();
  return (
    <div style={{ padding: "var(--space-4)", display: "grid", gap: "var(--space-3)" }}>
      <Message severity="error" text={apiErrorMessage(error)} />
      {onRetry ? (
        <div>
          <Button
            type="button"
            text
            icon="pi pi-refresh"
            label={t("common.retry")}
            onClick={onRetry}
          />
        </div>
      ) : null}
    </div>
  );
}

export function InlineError({ error }: { error: unknown }) {
  return <Message severity="error" text={apiErrorMessage(error)} style={{ width: "100%" }} />;
}
