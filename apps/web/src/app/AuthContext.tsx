import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { Session, User } from "@supabase/supabase-js";
import { getSupabaseClient, isSupabaseConfigured } from "../lib/supabase";

type AuthContextValue = {
  accessToken: string;
  configured: boolean;
  loading: boolean;
  session: Session | null;
  user: User | null;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(isSupabaseConfigured);

  useEffect(() => {
    if (!isSupabaseConfigured) {
      setLoading(false);
      return;
    }

    let active = true;
    let unsubscribe: (() => void) | undefined;

    void getSupabaseClient()
      .then(async (client) => {
        const { data } = await client.auth.getSession();
        if (!active) return;

        setSession(data.session);
        setLoading(false);
        const { data: listener } = client.auth.onAuthStateChange((_event, nextSession) => {
          if (!active) return;
          setSession(nextSession);
          setLoading(false);
        });
        unsubscribe = () => listener.subscription.unsubscribe();
      })
      .catch(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
      unsubscribe?.();
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      accessToken: session?.access_token ?? "",
      configured: isSupabaseConfigured,
      loading,
      session,
      user: session?.user ?? null,
      signOut: async () => {
        const client = await getSupabaseClient();
        await client.auth.signOut();
        setSession(null);
      },
    }),
    [loading, session],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
