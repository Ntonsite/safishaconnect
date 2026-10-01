import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { authApi, type CustomerRegisterBody, type ProviderRegisterBody } from "../api/endpoints";
import { ensureSession, tokens } from "../api/client";
import type { Me, Role, TokenPair } from "../api/types";
import { setLocale } from "../i18n";

interface AuthState {
  user: Me | null;
  ready: boolean;
  login: (identifier: string, password: string) => Promise<Me>;
  register: (body: CustomerRegisterBody) => Promise<Me>;
  registerProvider: (body: ProviderRegisterBody) => Promise<Me>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function homeFor(role: Role): string {
  return role === "ADMIN" ? "/admin" : role === "PROVIDER" ? "/provider" : "/app";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null);
  const [ready, setReady] = useState(false);
  const queryClient = useQueryClient();

  const loadMe = useCallback(async () => {
    const me = await authApi.me();
    setUser(me);
    return me;
  }, []);

  useEffect(() => {
    tokens.onExpired(() => {
      tokens.clear();
      setUser(null);
      queryClient.clear();
    });
    (async () => {
      try {
        if (await ensureSession()) await loadMe();
      } catch {
        tokens.clear();
      } finally {
        setReady(true);
      }
    })();
  }, [loadMe, queryClient]);

  const startSession = useCallback(
    async (pair: TokenPair) => {
      tokens.set(pair);
      queryClient.clear();
      const me = await loadMe();
      void setLocale(me.preferred_locale);
      return me;
    },
    [loadMe, queryClient],
  );

  const value = useMemo<AuthState>(
    () => ({
      user,
      ready,
      login: async (identifier, password) => startSession(await authApi.login(identifier, password)),
      register: async (body) => startSession(await authApi.register(body)),
      registerProvider: async (body) => startSession(await authApi.registerProvider(body)),
      logout: async () => {
        const refresh = tokens.refresh;
        tokens.clear();
        setUser(null);
        queryClient.clear();
        if (refresh) await authApi.logout(refresh).catch(() => undefined);
      },
      refreshUser: async () => {
        await loadMe();
      },
    }),
    [user, ready, startSession, loadMe, queryClient],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
