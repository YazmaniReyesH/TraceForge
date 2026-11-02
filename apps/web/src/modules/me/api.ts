// Llamadas a /api/v1/me (vistas transversales del usuario).

import { apiFetch } from "../../shared/api/client";
import type { MyProjectRead } from "./types";

export const meApi = {
  projects: () => apiFetch<MyProjectRead[]>("/me/projects"),
};
