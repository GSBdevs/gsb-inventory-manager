import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL as string;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

if (!url || !anonKey) {
  // Falha cedo e clara: sem essas envs o login não funciona.
  console.error("VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY ausentes — configure .env.local");
}

export const supabase = createClient(url, anonKey, {
  auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false },
});
