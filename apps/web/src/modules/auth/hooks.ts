// Queries / mutations de auth (TanStack Query).

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "../../shared/api/errors";
import { authApi } from "./api";
import type { RegisterRequest, UserRead } from "./types";

export const ME_KEY = ["auth", "me"] as const;

/** Usuario autenticado. 401 → null (no autenticado), no es un error de la query. */
export function useMe() {
  return useQuery<UserRead | null>({
    queryKey: ME_KEY,
    queryFn: async () => {
      try {
        return await authApi.me();
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          return null;
        }
        throw error;
      }
    },
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: authApi.login,
    onSuccess: (user) => qc.setQueryData(ME_KEY, user),
  });
}

export function useRegister() {
  const qc = useQueryClient();
  return useMutation({
    // Registro + inicio de sesión automático (register no emite sesión por sí mismo).
    mutationFn: async (body: RegisterRequest) => {
      await authApi.register(body);
      return authApi.login({ email: body.email, password: body.password });
    },
    onSuccess: (user) => qc.setQueryData(ME_KEY, user),
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      qc.setQueryData(ME_KEY, null);
      qc.clear();
    },
  });
}
