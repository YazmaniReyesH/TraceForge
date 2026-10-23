// ThemeProvider: expone el tema y el toggle; persiste en localStorage y sincroniza la clase del
// <html> y el stylesheet de PrimeReact. Arranca en CLARO. (El hook está en useTheme.ts.)

import { useCallback, useState, type ReactNode } from "react";

import { applyPrimeReactTheme } from "./primeTheme";
import { ThemeContext } from "./themeContext";
import { getStoredTheme, storeTheme, type Theme } from "./themeStorage";

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(getStoredTheme);

  const toggle = useCallback(() => {
    setThemeState((prev) => {
      const next: Theme = prev === "light" ? "dark" : "light";
      document.documentElement.classList.toggle("theme-dark", next === "dark");
      storeTheme(next);
      applyPrimeReactTheme(next);
      return next;
    });
  }, []);

  return <ThemeContext.Provider value={{ theme, toggle }}>{children}</ThemeContext.Provider>;
}
