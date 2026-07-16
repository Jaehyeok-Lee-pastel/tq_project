import type { SupabaseClient } from "@supabase/supabase-js";

// Frontend uses the ANON key only. Never put the service_role key here.
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "";
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || "";

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);

let clientPromise: Promise<SupabaseClient> | null = null;

export function getSupabaseClient(): Promise<SupabaseClient> {
  if (clientPromise) return clientPromise;

  clientPromise = import("@supabase/supabase-js").then(({ createClient }) =>
    createClient(supabaseUrl || "http://localhost:54321", supabaseAnonKey || "local-anon-key")
  );
  return clientPromise;
}
