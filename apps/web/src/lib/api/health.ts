/** Liveness lives at the API root (GET {API_URL}/health), outside /api/v1, per deploy-ops. */
export const HEALTH_PATH = "/health";

export async function checkHealth(baseUrl: string, timeoutMs = 5000): Promise<boolean> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${baseUrl.replace(/\/+$/, "")}${HEALTH_PATH}`, {
      signal: controller.signal,
      cache: "no-store",
    });
    return response.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}
