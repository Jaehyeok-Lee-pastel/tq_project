import { createClient } from "@supabase/supabase-js";

// Frontend uses the ANON key only. Never put the service_role key here.
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "";
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || "";

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);

export const supabase = createClient(
  supabaseUrl || "http://localhost:54321",
  supabaseAnonKey || "local-anon-key",
);
