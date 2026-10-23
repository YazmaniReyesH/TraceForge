// Tema claro/oscuro: tipo, clave de localStorage y lectura inicial. Arranca en CLARO.

export type Theme = "light" | "dark";

export const THEME_STORAGE_KEY = "tf-theme";

export function getStoredTheme(): Theme {
  try {
    return localStorage.getItem(THEME_STORAGE_KEY) === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

export function storeTheme(theme: Theme): void {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    /* localStorage no disponible: el tema no persiste, pero la app sigue funcionando */
  }
}
