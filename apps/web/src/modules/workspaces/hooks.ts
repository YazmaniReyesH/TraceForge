// Queries / mutations de workspaces (TanStack Query). Invalida tras cada mutación.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useMe } from "../auth/hooks";
import { workspacesApi } from "./api";
import type {
  TransferOwnershipRequest,
  WorkspaceMemberAdd,
  WorkspaceMemberRoleUpdate,
  WorkspaceRole,
} from "./types";

const LIST_KEY = ["workspaces"] as const;
const detailKey = (id: string) => ["workspace", id] as const;
const membersKey = (id: string) => ["workspace-members", id] as const;

export function useWorkspaces() {
  return useQuery({ queryKey: LIST_KEY, queryFn: workspacesApi.list });
}

export function useWorkspace(id: string | undefined) {
  return useQuery({
    queryKey: detailKey(id ?? "nil"),
    queryFn: () => workspacesApi.get(id as string),
    enabled: !!id,
  });
}

export function useWorkspaceMembers(id: string | undefined) {
  return useQuery({
    queryKey: membersKey(id ?? "nil"),
    queryFn: () => workspacesApi.members(id as string),
    enabled: !!id,
    retry: false,
  });
}

/** Rol del usuario actual en el workspace (derivado de la lista de miembros + /auth/me). */
export function useMyWorkspaceRole(id: string | undefined): WorkspaceRole | undefined {
  const { data: me } = useMe();
  const { data: members } = useWorkspaceMembers(id);
  if (!me || !members) return undefined;
  return members.find((m) => m.user_id === me.user_id)?.role;
}

export function useCreateWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: workspacesApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: LIST_KEY }),
  });
}

export function useUpdateWorkspace(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => workspacesApi.update(id, { name }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: LIST_KEY });
      void qc.invalidateQueries({ queryKey: detailKey(id) });
    },
  });
}

export function useDeleteWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => workspacesApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: LIST_KEY }),
  });
}

function useMembersInvalidation(id: string) {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: membersKey(id) });
    void qc.invalidateQueries({ queryKey: LIST_KEY });
  };
}

export function useAddWorkspaceMember(id: string) {
  const invalidate = useMembersInvalidation(id);
  return useMutation({
    mutationFn: (body: WorkspaceMemberAdd) => workspacesApi.addMember(id, body),
    onSuccess: invalidate,
  });
}

export function useUpdateWorkspaceMemberRole(id: string) {
  const invalidate = useMembersInvalidation(id);
  return useMutation({
    mutationFn: (vars: { userId: string; body: WorkspaceMemberRoleUpdate }) =>
      workspacesApi.updateMemberRole(id, vars.userId, vars.body),
    onSuccess: invalidate,
  });
}

export function useRemoveWorkspaceMember(id: string) {
  const invalidate = useMembersInvalidation(id);
  return useMutation({
    mutationFn: (userId: string) => workspacesApi.removeMember(id, userId),
    onSuccess: invalidate,
  });
}

export function useTransferWorkspaceOwnership(id: string) {
  const invalidate = useMembersInvalidation(id);
  return useMutation({
    mutationFn: (body: TransferOwnershipRequest) => workspacesApi.transferOwnership(id, body),
    onSuccess: invalidate,
  });
}
