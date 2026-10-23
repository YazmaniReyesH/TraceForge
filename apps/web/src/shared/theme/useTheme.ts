// Hook para consumir el tema actual y el toggle.

import { useContext } from "react";

import { ThemeContext, type ThemeContextValue } from "./themeContext";

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme debe usarse dentro de <ThemeProvider>");
  }
  return ctx;
}
