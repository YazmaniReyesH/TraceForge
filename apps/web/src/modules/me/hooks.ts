// Query de las vistas transversales del usuario.

import { useQuery } from "@tanstack/react-query";

import { meApi } from "./api";

export function useMyProjects() {
  return useQuery({ queryKey: ["me", "projects"], queryFn: meApi.projects });
}
