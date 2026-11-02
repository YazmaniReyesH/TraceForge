// Queries / mutations de projects (TanStack Query). Invalida tras cada mutación.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useMe } from "../auth/hooks";
import { useMyWorkspaceRole } from "../workspaces/hooks";
import { projectsApi } from "./api";
import type { ProjectMemberAdd, ProjectMemberRoleUpdate, ProjectRole } from "./types";

const listKey = (wid: string) => ["projects", wid] as const;
const detailKey = (wid: string, pid: string) => ["project", wid, pid] as const;
const membersKey = (wid: string, pid: string) => ["project-members", wid, pid] as const;

export function useProjects(wid: string) {
  return useQuery({ queryKey: listKey(wid), queryFn: () => projectsApi.list(wid) });
}

export function useProject(wid: string, pid: string | undefined) {
  return useQuery({
    queryKey: detailKey(wid, pid ?? "nil"),
    queryFn: () => projectsApi.get(wid, pid as string),
    enabled: !!pid,
    retry: false,
  });
}

export function useProjectMembers(wid: string, pid: string | undefined) {
  return useQuery({
    queryKey: membersKey(wid, pid ?? "nil"),
    queryFn: () => projectsApi.members(wid, pid as string),
    enabled: !!pid,
    retry: false,
  });
}

/** Rol EFECTIVO del usuario en el proyecto (owner/admin => lead; si no, su membresía). */
export function useMyEffectiveProjectRole(
  wid: string,
  pid: string | undefined,
): ProjectRole | undefined {
  const wsRole = useMyWorkspaceRole(wid);
  const { data: me } = useMe();
  const { data: members } = useProjectMembers(wid, pid);
  if (wsRole === "owner" || wsRole === "admin") return "lead";
  if (!me || !members) return undefined;
  return members.find((m) => m.user_id === me.user_id)?.role;
}

export function useCreateProject(wid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; classification?: string | null }) =>
      projectsApi.create(wid, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: listKey(wid) }),
  });
}

export function useUpdateProject(wid: string, pid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => projectsApi.update(wid, pid, { name }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: listKey(wid) });
      void qc.invalidateQueries({ queryKey: detailKey(wid, pid) });
    },
  });
}

export function useDeleteProject(wid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (pid: string) => projectsApi.remove(wid, pid),
    onSuccess: () => qc.invalidateQueries({ queryKey: listKey(wid) }),
  });
}

function useMembersInvalidation(wid: string, pid: string) {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: membersKey(wid, pid) });
  };
}

export function useAddProjectMember(wid: string, pid: string) {
  const invalidate = useMembersInvalidation(wid, pid);
  return useMutation({
    mutationFn: (body: ProjectMemberAdd) => projectsApi.addMember(wid, pid, body),
    onSuccess: invalidate,
  });
}

export function useUpdateProjectMemberRole(wid: string, pid: string) {
  const invalidate = useMembersInvalidation(wid, pid);
  return useMutation({
    mutationFn: (vars: { userId: string; body: ProjectMemberRoleUpdate }) =>
      projectsApi.updateMemberRole(wid, pid, vars.userId, vars.body),
    onSuccess: invalidate,
  });
}

export function useRemoveProjectMember(wid: string, pid: string) {
  const invalidate = useMembersInvalidation(wid, pid);
  return useMutation({
    mutationFn: (userId: string) => projectsApi.removeMember(wid, pid, userId),
    onSuccess: invalidate,
  });
}
