// Cliente HTTP de TraceForge.
// - credentials: "include" (cookie de sesión httpOnly).
// - CSRF double-submit (ADR-0010): en mutaciones envía X-CSRF-Token con el valor de la cookie tf_csrf.
// - Respuestas de error → ApiError con el `code` del envelope {code, message}.
// - El manejo global de 401 (sesión expirada → login) se cablea en el QueryClient (ver main.tsx).

import { ApiError } from "./errors";

const API_PREFIX = "/api/v1";
const CSRF_COOKIE = "tf_csrf";
const CSRF_HEADER = "X-CSRF-Token";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
}

interface ErrorEnvelope {
  code?: unknown;
  message?: unknown;
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (!SAFE_METHODS.has(method)) {
    const csrf = readCookie(CSRF_COOKIE);
    if (csrf) {
      headers[CSRF_HEADER] = csrf;
    }
  }

  let response: Response;
  try {
    response = await fetch(`${API_PREFIX}${path}`, {
      method,
      headers,
      credentials: "include",
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: options.signal,
    });
  } catch {
    throw new ApiError("network", 0);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const data: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const envelope = (data ?? {}) as ErrorEnvelope;
    const code = typeof envelope.code === "string" ? envelope.code : "unknown";
    const message = typeof envelope.message === "string" ? envelope.message : "";
    throw new ApiError(code, response.status, message);
  }

  return data as T;
}
