/**
 * Base API client for communicating with the Django backend.
 * Includes automatic JWT refresh on 401 responses.
 */

const API_BASE = "/api";

function getToken(key: string): string | null {
  return localStorage.getItem(key) || sessionStorage.getItem(key);
}

function setToken(key: string, value: string): void {
  if (sessionStorage.getItem("access_token") && !localStorage.getItem("access_token")) {
    sessionStorage.setItem(key, value);
  } else {
    localStorage.setItem(key, value);
  }
}

function clearTokens(): void {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  sessionStorage.removeItem("access_token");
  sessionStorage.removeItem("refresh_token");
}

export class ApiError extends Error {
  status: number;
  data: Record<string, unknown>;
  fieldErrors: Record<string, string[]>;

  constructor(status: number, statusText: string, data: Record<string, unknown> = {}) {
    super(`API ${status}: ${statusText}`);
    this.status = status;
    this.data = data;
    this.fieldErrors = Object.fromEntries(
      Object.entries(data).filter(
        ([, value]) => Array.isArray(value) && value.every((item) => typeof item === "string"),
      ),
    ) as Record<string, string[]>;
  }
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string>;
}

function buildUrl(endpoint: string, params?: Record<string, string>): string {
  const url = new URL(`${API_BASE}${endpoint}`, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }
  return url.toString();
}

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const token = getToken("access_token");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getToken("refresh_token");
  if (!refreshToken) return false;

  try {
    const res = await fetch(buildUrl("/auth/token/refresh/"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: refreshToken }),
    });

    if (!res.ok) return false;

    const data = await res.json();
    setToken("access_token", data.access);
    if (data.refresh) {
      setToken("refresh_token", data.refresh);
    }
    return true;
  } catch {
    return false;
  }
}

function tryRefresh(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = refreshAccessToken().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

function redirectToLogin() {
  clearTokens();
  if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
    window.location.href = "/login";
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorData: Record<string, unknown> = {};
    try {
      const body = await res.json();
      if (typeof body === "object" && body !== null) {
        errorData = body as Record<string, unknown>;
      }
    } catch {
      // response body wasn't JSON
    }
    throw new ApiError(res.status, res.statusText, errorData);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { params, headers: customHeaders, ...init } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...authHeaders(),
    ...((customHeaders as Record<string, string>) ?? {}),
  };

  const res = await fetch(buildUrl(endpoint, params), { ...init, headers });

  if (res.status === 401) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      const retryHeaders: Record<string, string> = {
        "Content-Type": "application/json",
        ...authHeaders(),
        ...((customHeaders as Record<string, string>) ?? {}),
      };
      const retryRes = await fetch(buildUrl(endpoint, params), { ...init, headers: retryHeaders });
      if (retryRes.status === 401) {
        redirectToLogin();
      }
      return handleResponse<T>(retryRes);
    }
    redirectToLogin();
    throw new ApiError(401, "Unauthorized");
  }

  return handleResponse<T>(res);
}

export const api = {
  get: <T>(endpoint: string, params?: Record<string, string>) =>
    request<T>(endpoint, { method: "GET", params }),

  post: <T>(endpoint: string, body: unknown) =>
    request<T>(endpoint, { method: "POST", body: JSON.stringify(body) }),

  put: <T>(endpoint: string, body: unknown) =>
    request<T>(endpoint, { method: "PUT", body: JSON.stringify(body) }),

  patch: <T>(endpoint: string, body: unknown) =>
    request<T>(endpoint, { method: "PATCH", body: JSON.stringify(body) }),

  delete: <T>(endpoint: string) =>
    request<T>(endpoint, { method: "DELETE" }),

  upload: async <T>(endpoint: string, formData: FormData): Promise<T> => {
    const res = await fetch(buildUrl(endpoint), {
      method: "POST",
      headers: authHeaders(),
      body: formData,
    });

    if (res.status === 401) {
      const refreshed = await tryRefresh();
      if (refreshed) {
        const retryRes = await fetch(buildUrl(endpoint), {
          method: "POST",
          headers: authHeaders(),
          body: formData,
        });
        if (retryRes.status === 401) redirectToLogin();
        return handleResponse<T>(retryRes);
      }
      redirectToLogin();
      throw new ApiError(401, "Unauthorized");
    }

    return handleResponse<T>(res);
  },
};
