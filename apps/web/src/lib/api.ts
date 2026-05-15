/**
 * Tiny typed API client. Wraps fetch + the auth token from localStorage.
 * Keep it intentionally small — the app uses TanStack Query for caching.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public payload: unknown,
  ) {
    super(message);
  }
}

function authHeader(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const token = window.localStorage.getItem('tcvn.access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function api<T>(
  path: string,
  init: RequestInit & { json?: unknown } = {},
): Promise<T> {
  const { json, headers, ...rest } = init;
  const res = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers: {
      ...(json !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...authHeader(),
      ...(headers as Record<string, string> | undefined),
    },
    body: json !== undefined ? JSON.stringify(json) : (rest.body as BodyInit | undefined),
  });

  if (!res.ok) {
    let payload: unknown = null;
    try {
      payload = await res.json();
    } catch {
      /* ignore */
    }
    throw new ApiError(res.statusText || 'API error', res.status, payload);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ---- Typed endpoint helpers ----
export interface Standard {
  id: string;
  code: string;
  title_vi: string;
  version: string;
  description?: string;
}

export const standardsApi = {
  list: () => api<Standard[]>('/standards'),
};

export interface Project {
  id: string;
  name: string;
  building_type: string;
  description?: string;
  created_at: string;
}

export const projectsApi = {
  list: () => api<Project[]>('/projects'),
  create: (body: { name: string; building_type: string; description?: string }) =>
    api<Project>('/projects', { method: 'POST', json: body }),
};
