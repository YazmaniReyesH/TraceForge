// Punto de entrada: fuentes, CSS base/tokens, PrimeReact, i18n, Query, Router y tema.

import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/jetbrains-mono/400.css";
import "primereact/resources/primereact.min.css";
import "primeicons/primeicons.css";
import "./shared/theme/tokens.css";
import "./shared/i18n";

import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PrimeReactProvider } from "primereact/api";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import { ME_KEY } from "./modules/auth/hooks";
import { ApiError } from "./shared/api/errors";
import { applyPrimeReactTheme } from "./shared/theme/primeTheme";
import { ThemeProvider } from "./shared/theme/ThemeProvider";
import { getStoredTheme } from "./shared/theme/themeStorage";

// El tema de PrimeReact se aplica ANTES del render (la clase del <html> ya la puso el
// script anti-parpadeo de index.html).
applyPrimeReactTheme(getStoredTheme());

// Manejo global de 401 (sesión expirada): se limpia la sesión y el guard lleva a /login.
function onApiError(error: unknown): void {
  if (error instanceof ApiError && error.status === 401) {
    queryClient.setQueryData(ME_KEY, null);
  }
}

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  queryCache: new QueryCache({ onError: onApiError }),
  mutationCache: new MutationCache({ onError: onApiError }),
});

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("No se encontró el elemento #root");
}

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <PrimeReactProvider>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </PrimeReactProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
);
