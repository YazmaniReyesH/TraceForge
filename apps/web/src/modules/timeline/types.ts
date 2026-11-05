// Tipos del timeline alineados al backend (generados desde OpenAPI).

import type { components } from "../../shared/api/types.gen";

export type SessionRead = components["schemas"]["SessionRead"];
export type SessionCreate = components["schemas"]["SessionCreate"];
export type SessionUpdate = components["schemas"]["SessionUpdate"];

export type EvidenceKind = components["schemas"]["EvidenceKind"];
export type EvidenceItemRead = components["schemas"]["EvidenceItemRead"];
export type EvidenceItemVersionRead = components["schemas"]["EvidenceItemVersionRead"];
export type EvidenceItemCreate = components["schemas"]["EvidenceItemCreate"];
export type EvidenceItemMove = components["schemas"]["EvidenceItemMove"];

// El detalle con historial no está en el OpenAPI porque el endpoint GET usa response_model=None
// (devuelve una unión EvidenceItemRead | EvidenceItemDetailRead según ?include_history). Lo
// componemos a partir de los tipos generados (no redefinimos campos): item vigente + historial.
export type EvidenceItemDetail = EvidenceItemRead & {
  history: EvidenceItemVersionRead[];
};
