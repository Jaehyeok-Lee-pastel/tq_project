import { supabase } from "./supabase";

export async function authenticatedFetch(input: RequestInfo | URL, init?: RequestInit) {
  const { data } = await supabase.auth.getSession();
  const headers = new Headers(init?.headers);
  if (data.session?.access_token) {
    headers.set("Authorization", `Bearer ${data.session.access_token}`);
  }
  return fetch(input, { ...init, headers });
}

export async function authenticatedJson<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  const response = await authenticatedFetch(input, init);
  if (!response.ok) {
    let detail = "";
    try {
      const payload = (await response.json()) as { detail?: string };
      detail = payload.detail ? `: ${payload.detail}` : "";
    } catch {
      detail = "";
    }
    throw new Error(`API 오류: ${response.status}${detail}`);
  }
  return (await response.json()) as T;
}
