// Enrutado: rutas públicas (/login, /register) y área protegida (shell + dominio).
// Las páginas se cargan con React.lazy (code-splitting): cada pantalla y su parte de PrimeReact
// viajan en chunks aparte, aligerando el bundle principal (el shell y el guard sí son eager).

import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./modules/auth/components/ProtectedRoute";
import { AppLayout } from "./shared/ui/AppLayout";
import { PageLoader } from "./shared/ui/PageLoader";

const LoginPage = lazy(() =>
  import("./modules/auth/pages/LoginPage").then((m) => ({ default: m.LoginPage })),
);
const RegisterPage = lazy(() =>
  import("./modules/auth/pages/RegisterPage").then((m) => ({ default: m.RegisterPage })),
);
const MyProjectsPage = lazy(() =>
  import("./modules/me/pages/MyProjectsPage").then((m) => ({ default: m.MyProjectsPage })),
);
const ProjectsPage = lazy(() =>
  import("./modules/projects/pages/ProjectsPage").then((m) => ({ default: m.ProjectsPage })),
);
const WorkspacesPage = lazy(() =>
  import("./modules/workspaces/pages/WorkspacesPage").then((m) => ({ default: m.WorkspacesPage })),
);
const TimelinePage = lazy(() =>
  import("./modules/timeline/pages/TimelinePage").then((m) => ({ default: m.TimelinePage })),
);

export default function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route index element={<Navigate to="/workspaces" replace />} />
            <Route path="projects" element={<MyProjectsPage />} />
            <Route path="workspaces" element={<WorkspacesPage />} />
            <Route path="workspaces/:workspaceId" element={<WorkspacesPage />} />
            <Route path="workspaces/:workspaceId/projects" element={<ProjectsPage />} />
            <Route path="workspaces/:workspaceId/projects/:projectId" element={<ProjectsPage />} />
            <Route
              path="workspaces/:workspaceId/projects/:projectId/timeline"
              element={<TimelinePage />}
            />
            <Route
              path="workspaces/:workspaceId/projects/:projectId/timeline/:sessionId"
              element={<TimelinePage />}
            />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
