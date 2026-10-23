// Botón de alternar tema claro/oscuro (usa el ThemeProvider; etiqueta por i18n).

import { Button } from "primereact/button";
import { useTranslation } from "react-i18next";

import { useTheme } from "../theme/useTheme";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const { t } = useTranslation();
  const label = theme === "dark" ? t("theme.toLight") : t("theme.toDark");
  return (
    <Button
      type="button"
      icon={theme === "dark" ? "pi pi-sun" : "pi pi-moon"}
      onClick={toggle}
      rounded
      text
      aria-label={label}
      tooltip={label}
      tooltipOptions={{ position: "bottom" }}
    />
  );
}
