// Shell protegido: header (marca, navegación, toggle de tema, usuario, logout) + contenido.
// Monta <ConfirmDialog/> una vez para las confirmaciones imperativas (acciones destructivas).

import { Button } from "primereact/button";
import { ConfirmDialog } from "primereact/confirmdialog";
import { useTranslation } from "react-i18next";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useLogout, useMe } from "../../modules/auth/hooks";
import { ThemeToggle } from "./ThemeToggle";
import "./layout.css";

export function AppLayout() {
  const { t } = useTranslation();
  const { data: user } = useMe();
  const logout = useLogout();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const onLogout = () => {
    logout.mutate(undefined, { onSuccess: () => navigate("/login", { replace: true }) });
  };

  // Resaltado EXACTO por sección (no por prefijo amplio):
  // - "Workspaces": la lista o el detalle de un workspace (/workspaces, /workspaces/:id), NO las
  //   rutas de project (/workspaces/:id/projects...). Así el detalle de proyecto no marca Workspaces.
  // - "Mis proyectos": /projects.
  const isWorkspacesSection = pathname === "/workspaces" || /^\/workspaces\/[^/]+$/.test(pathname);
  const isMyProjectsSection = pathname === "/projects" || pathname.startsWith("/projects/");
  const navClass = (active: boolean) =>
    active ? "tf-nav-link tf-nav-link--active" : "tf-nav-link";

  return (
    <div className="tf-shell">
      <ConfirmDialog />
      <header className="tf-header">
        <div className="tf-header-left">
          <Link to="/workspaces" className="tf-brand">
            {t("app.name")}
          </Link>
          <nav className="tf-nav">
            <Link to="/workspaces" className={navClass(isWorkspacesSection)}>
              {t("nav.workspaces")}
            </Link>
            <Link to="/projects" className={navClass(isMyProjectsSection)}>
              {t("nav.myProjects")}
            </Link>
          </nav>
        </div>
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
