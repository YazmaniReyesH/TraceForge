// Cliente mínimo contra el backend de TraceForge.
// En tandas futuras esto lo reemplaza el cliente generado desde OpenAPI
// (packages/shared). Por ahora, solo lo necesario para GET /health.

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export interface HealthResponse {
  status: string;
  version: string;
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_URL}/health`);
  if (!response.ok) {
    throw new Error(`El backend respondió ${response.status}`);
  }
  return (await response.json()) as HealthResponse;
}
