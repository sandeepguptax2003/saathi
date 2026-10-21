import { createClient, type SupabaseClient } from "@supabase/supabase-js";

import { env } from "@/lib/env";

let client: SupabaseClient | null = null;

/** Browser Supabase client (anon key only; the service role key never reaches the browser). */
export function getSupabase(): SupabaseClient {
  if (!client) {
    client = createClient(env.NEXT_PUBLIC_SUPABASE_URL, env.NEXT_PUBLIC_SUPABASE_ANON_KEY, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
        storageKey: "saathi.auth",
      },
    });
  }
  return client;
}

export async function getAccessToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  try {
    const { data } = await getSupabase().auth.getSession();
    return data.session?.access_token ?? null;
  } catch {
    return null;
  }
}
