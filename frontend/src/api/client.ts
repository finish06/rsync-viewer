// Thin fetch wrapper for /api/v1. Same-origin, cookie-authenticated
// (access_token cookie); a 401 sends the browser to the login page with a
// return URL so the SPA route is restored after sign-in.

export class ApiRequestError extends Error {
  readonly status: number;
  readonly errorCode: string | undefined;

  constructor(status: number, message: string, errorCode?: string) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.errorCode = errorCode;
  }
}

export const API_BASE = "/api/v1";

function redirectToLogin(): void {
  const returnUrl = window.location.pathname + window.location.search;
  window.location.assign(`/login?return_url=${encodeURIComponent(returnUrl)}`);
}

export type QueryValue = string | number | boolean | null | undefined;

/** Double-submit token: the server sets a non-httpOnly csrf_token cookie. */
export function csrfToken(): string {
  const match = document.cookie.match(/(?:^|;)\s*csrf_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

export function buildQuery(params: object): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params) as [string, QueryValue][]) {
    if (value === null || value === undefined || value === "") continue;
    search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

export async function fetchJson<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...((init.headers as Record<string, string> | undefined) ?? {}),
  };
  if (!SAFE_METHODS.has(method)) {
    headers["X-CSRF-Token"] = csrfToken();
    if (init.body !== undefined && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }
  }
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...init,
    method,
    headers,
  });

  if (response.status === 401) {
    redirectToLogin();
    throw new ApiRequestError(401, "Not authenticated", "UNAUTHENTICATED");
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    let code: string | undefined;
    try {
      const body = (await response.json()) as {
        message?: string;
        error_code?: string;
      };
      message = body.message ?? message;
      code = body.error_code;
    } catch {
      // non-JSON error body; keep the generic message
    }
    throw new ApiRequestError(response.status, message, code);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** JSON mutation helper: serialises the body and sends the CSRF header. */
export function mutateJson<T>(
  path: string,
  method: "POST" | "PUT" | "PATCH" | "DELETE",
  body?: unknown,
): Promise<T> {
  return fetchJson<T>(path, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
