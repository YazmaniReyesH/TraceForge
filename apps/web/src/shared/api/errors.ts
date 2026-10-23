// Errores de API: ApiError lleva el `code` estable del envelope del backend (ADR-0009) y se
// traduce a un mensaje i18n por ese code (nunca se muestra el texto crudo del backend al usuario).

import i18n from "../i18n";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(code: string, status: number, message = "") {
    super(message || code);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

/** Mensaje localizado para mostrar al usuario a partir del `code` del error. */
export function apiErrorMessage(error: unknown): string {
  const code = error instanceof ApiError ? error.code : "unknown";
  return i18n.t(`errors.${code}`, { defaultValue: i18n.t("errors.unknown") });
}
