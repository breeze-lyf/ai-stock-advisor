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
  timeout: 30000, // 30s — use per-request config for long AI calls
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

// -- Refresh token state --
let _isRefreshing = false;
let _refreshSubscribers: Array<(token: string) => void> = [];

function _onTokenRefreshed(newToken: string) {
  _refreshSubscribers.forEach((cb) => cb(newToken));
  _refreshSubscribers = [];
}

const MAX_RETRIES = 2;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config;

    // -- 401: attempt token refresh --
    if (error.response?.status === 401 && typeof window !== "undefined") {
      // Don't retry the refresh endpoint itself
      if (config?.url?.includes("/auth/refresh")) {
        localStorage.removeItem("token");
        localStorage.removeItem("refreshToken");
        window.location.href = "/login";
        return Promise.reject(error);
      }

      const refreshToken = localStorage.getItem("refreshToken");
      if (!refreshToken || config?._retry) {
        // No way to recover the session — clear and redirect immediately
        localStorage.removeItem("token");
        localStorage.removeItem("refreshToken");
        window.location.href = "/login";
        return Promise.reject(error);
      }

      if (_isRefreshing) {
        // Queue this request until the in-flight refresh completes
        return new Promise((resolve) => {
          _refreshSubscribers.push((newToken: string) => {
            config.headers.Authorization = `Bearer ${newToken}`;
            resolve(api(config));
          });
        });
      }

      config._retry = true;
      _isRefreshing = true;

      try {
        const res = await axios.post(`${baseURL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });
        const { access_token, refresh_token: newRefresh } = res.data;
        localStorage.setItem("token", access_token);
        if (newRefresh) localStorage.setItem("refreshToken", newRefresh);
        api.defaults.headers.common.Authorization = `Bearer ${access_token}`;
        _onTokenRefreshed(access_token);
        config.headers.Authorization = `Bearer ${access_token}`;
        return api(config);
      } catch {
        localStorage.removeItem("token");
        localStorage.removeItem("refreshToken");
        window.location.href = "/login";
        return Promise.reject(error);
      } finally {
        _isRefreshing = false;
      }
    }

    // 403 — forbidden, just reject
    if (error.response?.status === 403) {
      return Promise.reject(error);
    }

    // Retry on transient 5xx (not POST to avoid duplicate side-effects)
    const isRetryable =
      (!error.response || (error.response.status >= 500 && error.response.status < 600)) &&
      config?.method?.toLowerCase() !== "post";

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
