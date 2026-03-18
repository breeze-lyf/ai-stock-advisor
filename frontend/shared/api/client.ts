import axios from "axios";

const baseURL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/api$/, "");

const api = axios.create({
  baseURL,
  timeout: 180000,
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

    if (error.response?.status === 401 || error.response?.status === 403) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("token");
        if (!window.location.pathname.includes("/login")) {
          window.location.href = "/login";
        }
      }
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
