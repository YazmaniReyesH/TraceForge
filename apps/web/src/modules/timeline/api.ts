// Llamadas a /api/v1/workspaces/{wid}/projects/{pid}/sessions (y sus ítems de evidencia).

import { apiFetch } from "../../shared/api/client";
import type {
  EvidenceItemCreate,
  EvidenceItemDetail,
  EvidenceItemMove,
  EvidenceItemRead,
  SessionCreate,
  SessionRead,
  SessionUpdate,
} from "./types";

const base = (wid: string, pid: string) => `/workspaces/${wid}/projects/${pid}/sessions`;

export const timelineApi = {
  // Sesiones
  listSessions: (wid: string, pid: string) => apiFetch<SessionRead[]>(base(wid, pid)),
  createSession: (wid: string, pid: string, body: SessionCreate) =>
    apiFetch<SessionRead>(base(wid, pid), { method: "POST", body }),
  renameSession: (wid: string, pid: string, sid: string, body: SessionUpdate) =>
    apiFetch<SessionRead>(`${base(wid, pid)}/${sid}`, { method: "PATCH", body }),
  deleteSession: (wid: string, pid: string, sid: string) =>
    apiFetch<void>(`${base(wid, pid)}/${sid}`, { method: "DELETE" }),

  // Ítems de evidencia
  listItems: (wid: string, pid: string, sid: string) =>
    apiFetch<EvidenceItemRead[]>(`${base(wid, pid)}/${sid}/items`),
  addItem: (wid: string, pid: string, sid: string, body: EvidenceItemCreate) =>
    apiFetch<EvidenceItemRead>(`${base(wid, pid)}/${sid}/items`, { method: "POST", body }),
  getItemDetail: (wid: string, pid: string, sid: string, itemId: string) =>
    apiFetch<EvidenceItemDetail>(`${base(wid, pid)}/${sid}/items/${itemId}?include_history=true`),
  editItem: (wid: string, pid: string, sid: string, itemId: string, body: EvidenceItemCreate) =>
    apiFetch<EvidenceItemRead>(`${base(wid, pid)}/${sid}/items/${itemId}`, {
      method: "PATCH",
      body,
    }),
  moveItem: (wid: string, pid: string, sid: string, itemId: string, body: EvidenceItemMove) =>
    apiFetch<EvidenceItemRead>(`${base(wid, pid)}/${sid}/items/${itemId}/move`, {
      method: "PATCH",
      body,
    }),
  deleteItem: (wid: string, pid: string, sid: string, itemId: string) =>
    apiFetch<void>(`${base(wid, pid)}/${sid}/items/${itemId}`, { method: "DELETE" }),
};
