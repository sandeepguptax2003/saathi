"use client";

import { useCallback } from "react";

// Loaded on demand so the landing page doesn't ship the Supabase SDK up front.
const loadSupabase = () => import("@/lib/supabase/client").then((m) => m.getSupabase());

function redirectTo(path = "/console"): string {
  return `${window.location.origin}${path}`;
}

export function useAuthActions() {
  const signInWithGoogle = useCallback(async () => {
    const { error } = await (
      await loadSupabase()
    ).auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: redirectTo() },
    });
    if (error) throw error;
  }, []);

  const sendMagicLink = useCallback(async (email: string) => {
    const { error } = await (
      await loadSupabase()
    ).auth.signInWithOtp({
      email,
      options: { emailRedirectTo: redirectTo() },
    });
    if (error) throw error;
  }, []);

  /** "Try demo": anonymous Supabase session; the API scopes it to seeded demo data. */
  const startDemo = useCallback(async () => {
    const supabase = await loadSupabase();
    const { data } = await supabase.auth.getSession();
    if (data.session) return;
    const { error } = await supabase.auth.signInAnonymously();
    if (error) throw error;
  }, []);

  const signOut = useCallback(async () => {
    const { error } = await (await loadSupabase()).auth.signOut();
    if (error) throw error;
  }, []);

  return { signInWithGoogle, sendMagicLink, startDemo, signOut };
}
