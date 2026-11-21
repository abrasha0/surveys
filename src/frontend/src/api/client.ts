const API_BASE = import.meta.env.VITE_API_BASE ?? '';
export const LOGIN_PATH = '/api/auth/login';

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

function detailMessage(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && 'message' in detail && typeof detail.message === 'string') {
    return detail.message;
  }
  return fallback;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  // A 401 from the login endpoint means a wrong password; let the caller show it.
  if (res.status === 401 && path !== LOGIN_PATH) {
    window.location.href = '/login';
    throw new ApiError(401, 'Not authenticated');
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, detailMessage(body.detail, res.statusText), body.detail);
  }

  return res.json();
}
