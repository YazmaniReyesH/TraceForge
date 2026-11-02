// Llamadas a /api/v1/workspaces (y sus membresías / transferencia).

import { apiFetch } from "../../shared/api/client";
import type {
  TransferOwnershipRequest,
  WorkspaceCreate,
  WorkspaceMemberAdd,
  WorkspaceMemberRead,
  WorkspaceMemberRoleUpdate,
  WorkspaceRead,
  WorkspaceUpdate,
} from "./types";

export const workspacesApi = {
  list: () => apiFetch<WorkspaceRead[]>("/workspaces"),
  get: (id: string) => apiFetch<WorkspaceRead>(`/workspaces/${id}`),
  create: (body: WorkspaceCreate) =>
    apiFetch<WorkspaceRead>("/workspaces", { method: "POST", body }),
  update: (id: string, body: WorkspaceUpdate) =>
    apiFetch<WorkspaceRead>(`/workspaces/${id}`, { method: "PATCH", body }),
  remove: (id: string) => apiFetch<void>(`/workspaces/${id}`, { method: "DELETE" }),

  members: (id: string) => apiFetch<WorkspaceMemberRead[]>(`/workspaces/${id}/members`),
  addMember: (id: string, body: WorkspaceMemberAdd) =>
    apiFetch<WorkspaceMemberRead>(`/workspaces/${id}/members`, { method: "POST", body }),
  updateMemberRole: (id: string, userId: string, body: WorkspaceMemberRoleUpdate) =>
    apiFetch<WorkspaceMemberRead>(`/workspaces/${id}/members/${userId}`, {
      method: "PATCH",
      body,
    }),
  removeMember: (id: string, userId: string) =>
    apiFetch<void>(`/workspaces/${id}/members/${userId}`, { method: "DELETE" }),
  transferOwnership: (id: string, body: TransferOwnershipRequest) =>
    apiFetch<void>(`/workspaces/${id}/transfer-ownership`, { method: "POST", body }),
};
