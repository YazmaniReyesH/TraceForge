// Queries / mutations del timeline (TanStack Query). Invalida tras cada mutación.
// El reordenamiento (move) es OPTIMISTA: reordena la lista en caché al instante y reconcilia
// (si el backend falla, revierte y deja que el error se muestre).

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { timelineApi } from "./api";
import type { EvidenceItemCreate, EvidenceItemRead, SessionCreate } from "./types";

const sessionsKey = (wid: string, pid: string) => ["sessions", wid, pid] as const;
const itemsKey = (wid: string, pid: string, sid: string) => ["items", wid, pid, sid] as const;
const itemDetailKey = (wid: string, pid: string, sid: string, itemId: string) =>
  ["item-detail", wid, pid, sid, itemId] as const;

// ── Sesiones ──
export function useSessions(wid: string, pid: string) {
  return useQuery({
    queryKey: sessionsKey(wid, pid),
    queryFn: () => timelineApi.listSessions(wid, pid),
  });
}

export function useCreateSession(wid: string, pid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SessionCreate) => timelineApi.createSession(wid, pid, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: sessionsKey(wid, pid) }),
  });
}

export function useRenameSession(wid: string, pid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { sid: string; name: string }) =>
      timelineApi.renameSession(wid, pid, vars.sid, { name: vars.name }),
    onSuccess: () => qc.invalidateQueries({ queryKey: sessionsKey(wid, pid) }),
  });
}

export function useDeleteSession(wid: string, pid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sid: string) => timelineApi.deleteSession(wid, pid, sid),
    onSuccess: () => qc.invalidateQueries({ queryKey: sessionsKey(wid, pid) }),
  });
}

// ── Ítems ──
export function useItems(wid: string, pid: string, sid: string | undefined) {
  return useQuery({
    queryKey: itemsKey(wid, pid, sid ?? "nil"),
    queryFn: () => timelineApi.listItems(wid, pid, sid as string),
    enabled: !!sid,
    retry: false,
  });
}

export function useItemDetail(wid: string, pid: string, sid: string, itemId: string | undefined) {
  return useQuery({
    queryKey: itemDetailKey(wid, pid, sid, itemId ?? "nil"),
    queryFn: () => timelineApi.getItemDetail(wid, pid, sid, itemId as string),
    enabled: !!itemId,
    retry: false,
  });
}

export function useAddItem(wid: string, pid: string, sid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: EvidenceItemCreate) => timelineApi.addItem(wid, pid, sid, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: itemsKey(wid, pid, sid) }),
  });
}

export function useEditItem(wid: string, pid: string, sid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { itemId: string; body: EvidenceItemCreate }) =>
      timelineApi.editItem(wid, pid, sid, vars.itemId, vars.body),
    onSuccess: (_data, vars) => {
      void qc.invalidateQueries({ queryKey: itemsKey(wid, pid, sid) });
      void qc.invalidateQueries({ queryKey: itemDetailKey(wid, pid, sid, vars.itemId) });
    },
  });
}

export function useDeleteItem(wid: string, pid: string, sid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (itemId: string) => timelineApi.deleteItem(wid, pid, sid, itemId),
    onSuccess: () => qc.invalidateQueries({ queryKey: itemsKey(wid, pid, sid) }),
  });
}

/** Reordena localmente: coloca `itemId` justo después de `afterId` (null = al inicio). */
function reorderLocally(
  items: EvidenceItemRead[],
  itemId: string,
  afterId: string | null,
): EvidenceItemRead[] {
  const moving = items.find((i) => i.evidence_item_id === itemId);
  if (!moving) return items;
  const rest = items.filter((i) => i.evidence_item_id !== itemId);
  if (afterId === null) return [moving, ...rest];
  const idx = rest.findIndex((i) => i.evidence_item_id === afterId);
  if (idx < 0) return items;
  return [...rest.slice(0, idx + 1), moving, ...rest.slice(idx + 1)];
}

export function useMoveItem(wid: string, pid: string, sid: string) {
  const qc = useQueryClient();
  const key = itemsKey(wid, pid, sid);
  return useMutation({
    mutationFn: (vars: { itemId: string; afterItemId: string | null }) =>
      timelineApi.moveItem(wid, pid, sid, vars.itemId, { after_item_id: vars.afterItemId }),
    onMutate: async (vars) => {
      await qc.cancelQueries({ queryKey: key });
      const previous = qc.getQueryData<EvidenceItemRead[]>(key);
      if (previous) {
        qc.setQueryData<EvidenceItemRead[]>(
          key,
          reorderLocally(previous, vars.itemId, vars.afterItemId),
        );
      }
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) qc.setQueryData(key, context.previous); // revertir
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: key }); // reconciliar con el backend
    },
  });
}
