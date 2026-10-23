// Contexto de tema (separado del provider y del hook para que cada archivo exporte una sola cosa).

import { createContext } from "react";

import type { Theme } from "./themeStorage";

export interface ThemeContextValue {
  theme: Theme;
  toggle: () => void;
}

export const ThemeContext = createContext<ThemeContextValue | null>(null);
