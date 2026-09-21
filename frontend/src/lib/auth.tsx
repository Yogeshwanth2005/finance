import { createContext, useContext, useMemo } from "react";
import type { ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { apiGet, apiPatch, apiPost } from "@/lib/api";
import type { User, UserSettings } from "@/lib/types";

interface AuthContextValue {
  user: User | null | undefined;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (name: string, email: string, password: string) => Promise<User>;
  updateSettings: (settings: UserSettings) => Promise<User>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

async function loadSession(): Promise<User | null> {
  return apiGet<User | null>("/auth/session");
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const session = useQuery({ queryKey: ["auth", "me"], queryFn: loadSession, retry: false });
  const user = session.data ?? (session.isPending ? undefined : null);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    isLoading: session.isPending,
    login: async (email, password) => {
      const nextUser = await apiPost<User>("/auth/login", { email, password });
      queryClient.setQueryData(["auth", "me"], nextUser);
      return nextUser;
    },
    register: async (name, email, password) => {
      const nextUser = await apiPost<User>("/auth/register", { name, email, password });
      queryClient.setQueryData(["auth", "me"], nextUser);
      return nextUser;
    },
    updateSettings: async (settings) => {
      const nextUser = await apiPatch<User>("/auth/settings", settings);
      queryClient.setQueryData(["auth", "me"], nextUser);
      return nextUser;
    },
    logout: async () => {
      await apiPost<{ message: string }>("/auth/logout");
      queryClient.setQueryData(["auth", "me"], null);
      queryClient.removeQueries({ queryKey: ["profile"] });
    },
  }), [queryClient, session.isPending, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}