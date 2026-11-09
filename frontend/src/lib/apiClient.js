import axios from "axios";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "/api";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
  timeout: 30000,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isCancel(error)) {
      return Promise.reject({
        status: null,
        code: "request_cancelled",
        message: "Request cancelled.",
        details: null,
        requestId: null,
        cancelled: true,
      });
    }

    const body = error.response?.data;
    const normalizedError = {
      status: error.response?.status ?? null,
      code: body?.error?.code ?? "network_error",
      message:
        body?.error?.message ??
        error.message ??
        "Something went wrong. Please try again.",
      details: body?.error?.details ?? null,
      requestId: body?.error?.request_id ?? null,
      cancelled: false,
    };

    return Promise.reject(normalizedError);
  },
);

export default apiClient;
