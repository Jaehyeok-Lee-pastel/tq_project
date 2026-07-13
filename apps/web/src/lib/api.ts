export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:7000";

async function handle<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = "";
    try {
      const errorBody = await response.json();
      detail = typeof errorBody.detail === "string" ? `: ${errorBody.detail}` : "";
    } catch {
      detail = "";
    }
    throw new Error(`API request failed: ${response.status}${detail}`);
  }
  return response.json() as Promise<T>;
}

function authHeaders(token?: string): HeadersInit | undefined {
  return token ? { Authorization: `Bearer ${token}` } : undefined;
}

export async function apiGet<T>(path: string, token?: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: authHeaders(token)
  });
  return handle<T>(response);
}

export async function apiPost<T>(path: string, body: unknown, token?: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(authHeaders(token) ?? {}) },
    body: JSON.stringify(body)
  });
  return handle<T>(response);
}

export async function apiPatch<T>(path: string, body: unknown, token?: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...(authHeaders(token) ?? {}) },
    body: JSON.stringify(body)
  });
  return handle<T>(response);
}

export async function apiDelete(path: string, token?: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "DELETE",
    headers: authHeaders(token)
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
}
