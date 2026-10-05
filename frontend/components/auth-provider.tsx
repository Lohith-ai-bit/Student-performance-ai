"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { dashboardPathForRole } from "@/lib/auth";
import type { AuthSession, Role, User } from "@/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (session: AuthSession) => void;
  logout: () => void;
  hasRole: (...roles: Role[]) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // hydrate from localStorage on first client render
    import("@/lib/auth").then(({ getStoredUser }) => {
      setUser(getStoredUser());
      setLoading(false);
    });
  }, []);

  const login = useCallback(
    (session: AuthSession) => {
      import("@/lib/auth").then(({ saveSession }) => {
        saveSession(session);
        setUser(session.user);
        router.replace(dashboardPathForRole(session.user.role));
      });
    },
    [router],
  );

  const logout = useCallback(() => {
    import("@/lib/auth").then(({ clearSession }) => {
      clearSession();
      setUser(null);
      router.replace("/login");
    });
  }, [router]);

  const hasRole = useCallback((...roles: Role[]) => (user ? roles.includes(user.role) : false), [user]);

  const value = useMemo(() => ({ user, loading, login, logout, hasRole }), [user, loading, login, logout, hasRole]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
