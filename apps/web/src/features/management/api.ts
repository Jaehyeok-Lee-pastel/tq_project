import { API_BASE_URL } from "../../lib/api";
import { authenticatedJson } from "../../lib/authApi";

export function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  return authenticatedJson<T>(`${API_BASE_URL}${path}`, init);
}
