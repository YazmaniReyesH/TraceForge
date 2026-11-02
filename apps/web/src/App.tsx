// Enrutado: rutas públicas (/login, /register) y área protegida (shell + dominio).

import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./modules/auth/components/ProtectedRoute";
import { LoginPage } from "./modules/auth/pages/LoginPage";
import { RegisterPage } from "./modules/auth/pages/RegisterPage";
import { MyProjectsPage } from "./modules/me/pages/MyProjectsPage";
import { ProjectsPage } from "./modules/projects/pages/ProjectsPage";
import { WorkspacesPage } from "./modules/workspaces/pages/WorkspacesPage";
import { AppLayout } from "./shared/ui/AppLayout";

export default function App() {
  return (
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
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
