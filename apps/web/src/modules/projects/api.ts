// Llamadas a /api/v1/workspaces/{wid}/projects (y sus membresías).

import { apiFetch } from "../../shared/api/client";
import type {
  ProjectCreate,
  ProjectMemberAdd,
  ProjectMemberRead,
  ProjectMemberRoleUpdate,
  ProjectRead,
  ProjectUpdate,
} from "./types";

const base = (wid: string) => `/workspaces/${wid}/projects`;

export const projectsApi = {
  list: (wid: string) => apiFetch<ProjectRead[]>(base(wid)),
  get: (wid: string, pid: string) => apiFetch<ProjectRead>(`${base(wid)}/${pid}`),
  create: (wid: string, body: ProjectCreate) =>
    apiFetch<ProjectRead>(base(wid), { method: "POST", body }),
  update: (wid: string, pid: string, body: ProjectUpdate) =>
    apiFetch<ProjectRead>(`${base(wid)}/${pid}`, { method: "PATCH", body }),
  remove: (wid: string, pid: string) => apiFetch<void>(`${base(wid)}/${pid}`, { method: "DELETE" }),

  members: (wid: string, pid: string) =>
    apiFetch<ProjectMemberRead[]>(`${base(wid)}/${pid}/members`),
  addMember: (wid: string, pid: string, body: ProjectMemberAdd) =>
    apiFetch<ProjectMemberRead>(`${base(wid)}/${pid}/members`, { method: "POST", body }),
  updateMemberRole: (wid: string, pid: string, userId: string, body: ProjectMemberRoleUpdate) =>
    apiFetch<ProjectMemberRead>(`${base(wid)}/${pid}/members/${userId}`, {
      method: "PATCH",
      body,
    }),
  removeMember: (wid: string, pid: string, userId: string) =>
    apiFetch<void>(`${base(wid)}/${pid}/members/${userId}`, { method: "DELETE" }),
};
