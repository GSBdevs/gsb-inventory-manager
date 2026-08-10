import { supabase } from "@/lib/supabase";

const BASE = "/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface RequestOptions {
  method?: string;
  json?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
}

export async function api<T = unknown>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = new URL(BASE + path, window.location.origin);
  for (const [key, value] of Object.entries(options.params ?? {})) {
    if (value !== undefined && value !== "") url.searchParams.set(key, String(value));
  }

  // O supabase-js renova o access token automaticamente; pegamos o atual da sessão.
  const { data } = await supabase.auth.getSession();
  const headers: Record<string, string> = {};
  if (data.session?.access_token) headers.Authorization = `Bearer ${data.session.access_token}`;
  if (options.json !== undefined) headers["Content-Type"] = "application/json";

  const resp = await fetch(url, {
    method: options.method ?? "GET",
    headers,
    body: options.json !== undefined ? JSON.stringify(options.json) : undefined,
  });

  if (resp.status === 401) {
    await supabase.auth.signOut();
    window.location.assign("/login");
    throw new ApiError(401, "Sessão expirada");
  }

  if (!resp.ok) {
    let detail = `Erro ${resp.status}`;
    try {
      const body = (await resp.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) {
        detail = body.detail.map((d: { msg?: string }) => d.msg ?? "").filter(Boolean).join("; ");
      }
    } catch {
      /* corpo não-JSON */
    }
    throw new ApiError(resp.status, detail);
  }

  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}
