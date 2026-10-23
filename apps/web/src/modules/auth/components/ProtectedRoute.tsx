// Guard: exige sesión. Mientras hidrata muestra loader; sin sesión redirige a /login.

import { Navigate, Outlet } from "react-router-dom";

import { PageLoader } from "../../../shared/ui/PageLoader";
import { useMe } from "../hooks";

export function ProtectedRoute() {
  const { data: user, isLoading } = useMe();

  if (isLoading) {
    return <PageLoader />;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}
