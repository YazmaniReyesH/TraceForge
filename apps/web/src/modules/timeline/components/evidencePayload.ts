// Tipos y helpers del formulario de evidencia (separados del componente para no romper el
// fast-refresh: un archivo de componente solo debe exportar componentes).

import type { EvidenceItemCreate, EvidenceKind } from "../types";

export interface EvidenceFormValues {
  kind: EvidenceKind;
  command_text: string;
  command_output: string;
  tool: string;
  language: string;
  note_text: string;
}

export function emptyValues(kind: EvidenceKind = "command"): EvidenceFormValues {
  return { kind, command_text: "", command_output: "", tool: "", language: "", note_text: "" };
}

/** Construye el cuerpo para el backend según el kind (vacíos → null en campos opcionales). */
export function toCreatePayload(v: EvidenceFormValues): EvidenceItemCreate {
  if (v.kind === "command") {
    return {
      kind: "command",
      command_text: v.command_text,
      command_output: v.command_output.trim() ? v.command_output : null,
      tool: v.tool.trim() ? v.tool : null,
      language: v.language.trim() ? v.language : null,
    };
  }
  return { kind: "note", note_text: v.note_text };
}
