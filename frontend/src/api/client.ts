// Thin fetch wrapper with Bearer token injection and basic error handling.

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export type ApiError = {
  status: number;
  message: string;
};

export type ApiResponse<T> = {
  data: T | null;
  error: ApiError | null;
};

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";
const TOKEN_STORAGE_KEY = "access_token";
const LOGIN_PATH = "/login"; // redirect target on 401

function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

function buildHeaders(extra?: HeadersInit): HeadersInit {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...extra,
  };
  const token = getToken();
  if (token) {
    return { ...headers, Authorization: `Bearer ${token}` };
  }
  return headers;
}

function buildUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return `${API_BASE}${path}`;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { method?: HttpMethod } = {}
): Promise<ApiResponse<T>> {
  const url = buildUrl(path);
  const { method = "GET", headers, body, ...rest } = options;
  const init: RequestInit = {
    method,
    headers: buildHeaders(headers),
    body,
    ...rest,
  };
  try {
    const res = await fetch(url, init);
    if (res.status === 401) {
      // Redirect to login for re-auth; keep error response for caller if needed.
      window.location.replace(LOGIN_PATH);
      return { data: null, error: { status: 401, message: "unauthorized" } };
    }
    let json: any = null;
    try {
      json = await res.json();
    } catch {
      json = null;
    }
    if (!res.ok) {
      const detail = json?.detail ?? res.statusText;
      return { data: null, error: { status: res.status, message: String(detail) } };
    }
    return { data: json as T, error: null };
  } catch (err) {
    return { data: null, error: { status: 0, message: (err as Error).message } };
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch {
    // ignore storage errors
  }
}

export function getStoredToken(): string | null {
  return getToken();
}
