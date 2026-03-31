import axios from "axios";

function getApiBaseURL(): string {
  // Browser: ALWAYS use relative URLs so Next.js rewrites proxy to the backend.
  // Must be checked FIRST - NEXT_PUBLIC_* vars are inlined at build time (always truthy),
  // so checking them first would make this branch unreachable.
  if (typeof window !== "undefined") {
    return "";
  }

  // Server-side rendering: use the explicit backend URL
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configured) {
    return configured.replace(/\/api\/?$/, "");
  }

  return "http://localhost:8000";
}

const baseURL = getApiBaseURL();

const api = axios.create({
  baseURL,
  timeout: 300000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

const MAX_RETRIES = 2;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config;

    // Do NOT clear the token or hard-redirect here.
    // AuthContext's route guard handles auth state and redirects.
    // The old logic cleared localStorage and did window.location.href="/login"
    // on every 401, which caused a logout loop when 401s came from
    // FastAPI trailing-slash redirects that dropped the Authorization header.
    if (error.response?.status === 401 || error.response?.status === 403) {
      return Promise.reject(error);
    }

    const isRetryable =
      (!error.response || (error.response.status >= 500 && error.response.status < 600)) &&
      config.method?.toLowerCase() !== "post"; // Skip post requests to avoid double-triggers on slow tasks

    if (isRetryable && config && !config.__isRetry) {
      config.__retryCount = config.__retryCount || 0;
      if (config.__retryCount < MAX_RETRIES) {
        config.__retryCount += 1;
        config.__isRetry = true;

        const delay = config.__retryCount * 1000;
        console.warn(
          `[API Retry] ${config.method?.toUpperCase()} ${config.url} attempt ${config.__retryCount}/${MAX_RETRIES} after ${delay}ms`
        );
        await new Promise((resolve) => setTimeout(resolve, delay));

        config.__isRetry = false;
        return api(config);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
