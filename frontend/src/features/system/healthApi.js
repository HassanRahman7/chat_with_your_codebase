import apiClient from "../../lib/apiClient";

/**
 * Fetch API/dependency health.
 *
 * A 503 response still carries a valid health body (degraded), so it is
 * treated as a resolved response rather than a network error.
 */
export async function getSystemHealth(signal) {
  const response = await apiClient.get("/health", {
    signal,
    timeout: 8000,
    validateStatus: (status) =>
      (status >= 200 && status < 300) || status === 503,
  });

  return { httpStatus: response.status, ...response.data };
}
