export interface HealthResponse {
  status: "ok";
  api_version: string;
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${apiBaseUrl}/health`, { signal });

  if (!response.ok) {
    throw new Error(`Backend health check failed (${response.status}).`);
  }

  return (await response.json()) as HealthResponse;
}
