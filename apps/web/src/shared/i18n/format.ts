// Formato de fecha/hora locale-aware (Intl), no manual. Usa el idioma por defecto de la app.

import { DEFAULT_LANGUAGE } from "./index";

const dateFormatter = new Intl.DateTimeFormat(DEFAULT_LANGUAGE, {
  dateStyle: "medium",
  timeStyle: "short",
});

export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : dateFormatter.format(date);
}
