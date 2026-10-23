// Estado de carga a pantalla completa (reutilizable).

import { ProgressSpinner } from "primereact/progressspinner";
import { useTranslation } from "react-i18next";

export function PageLoader() {
  const { t } = useTranslation();
  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        minHeight: "60vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "var(--space-3)",
        color: "var(--text-muted)",
      }}
    >
      <ProgressSpinner style={{ width: "48px", height: "48px" }} strokeWidth="4" />
      <span>{t("common.loading")}</span>
    </div>
  );
}
