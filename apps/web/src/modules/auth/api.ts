// Llamadas a /api/v1/auth.

import { apiFetch } from "../../shared/api/client";
import type { LoginRequest, RegisterRequest, UserRead } from "./types";

export const authApi = {
  me: () => apiFetch<UserRead>("/auth/me"),
  login: (body: LoginRequest) => apiFetch<UserRead>("/auth/login", { method: "POST", body }),
  register: (body: RegisterRequest) =>
    apiFetch<UserRead>("/auth/register", { method: "POST", body }),
  logout: () => apiFetch<void>("/auth/logout", { method: "POST" }),
};
