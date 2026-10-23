// Enrutado: rutas públicas (/login, /register) y área protegida (guard de sesión).

import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./modules/auth/components/ProtectedRoute";
import { LoginPage } from "./modules/auth/pages/LoginPage";
import { RegisterPage } from "./modules/auth/pages/RegisterPage";
import { HomePage } from "./modules/home/pages/HomePage";
import { AppLayout } from "./shared/ui/AppLayout";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<HomePage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
