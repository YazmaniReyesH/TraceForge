// Shell protegido: header (marca, toggle de tema, usuario, logout) + contenido (Outlet).

import { Button } from "primereact/button";
import { useTranslation } from "react-i18next";
import { Outlet, useNavigate } from "react-router-dom";

import { useLogout, useMe } from "../../modules/auth/hooks";
import { ThemeToggle } from "./ThemeToggle";
import "./layout.css";

export function AppLayout() {
  const { t } = useTranslation();
  const { data: user } = useMe();
  const logout = useLogout();
  const navigate = useNavigate();

  const onLogout = () => {
    logout.mutate(undefined, { onSuccess: () => navigate("/login", { replace: true }) });
  };

  return (
    <div className="tf-shell">
      <header className="tf-header">
        <span className="tf-brand">{t("app.name")}</span>
        <div className="tf-header-actions">
          <ThemeToggle />
          {user ? <span className="tf-user">{user.display_name}</span> : null}
          <Button
            type="button"
            text
            icon="pi pi-sign-out"
            label={t("nav.logout")}
            onClick={onLogout}
            loading={logout.isPending}
          />
        </div>
      </header>
      <main className="tf-main">
        <Outlet />
      </main>
    </div>
  );
}
