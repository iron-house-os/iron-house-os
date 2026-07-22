import { PropsWithChildren, createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { AuthUser, authApi } from "../api/auth";
import { AUTH_SESSION_EXPIRED_EVENT } from "../api/client";
import { fieldOperationsApi } from "../api/fieldOperations";

export type PortalRole = "employee" | "operator" | "foreman" | "management" | null;

type AuthContextValue = {
  user: AuthUser | null;
  isLoading: boolean;
  portalRole: PortalRole;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [portalRole, setPortalRole] = useState<PortalRole>(null);

  const resolvePortalRole = useCallback(async (account: AuthUser | null) => {
    if (!account) { setPortalRole(null); return; }
    if (account.role !== "viewer") { setPortalRole("management"); return; }
    try {
      const field = await fieldOperationsApi.bootstrap();
      setPortalRole(field.employees.find((item) => item.email.toLowerCase() === account.email.toLowerCase())?.portal_role ?? "employee");
    } catch { setPortalRole("employee"); }
  }, []);

  useEffect(() => {
    let active = true;
    authApi
      .me()
      .then((account) => {
        if (active) { setUser(account); return resolvePortalRole(account); }
      })
      .catch(() => {
        if (active) setUser(null);
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [resolvePortalRole]);

  useEffect(() => {
    const expireSession = () => setUser(null);
    window.addEventListener(AUTH_SESSION_EXPIRED_EVENT, expireSession);
    return () => window.removeEventListener(AUTH_SESSION_EXPIRED_EVENT, expireSession);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const account = await authApi.login(email, password); setUser(account); await resolvePortalRole(account);
  }, [resolvePortalRole]);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
      setPortalRole(null);
    }
  }, []);

  const changePassword = useCallback(async (currentPassword: string, newPassword: string) => {
    setUser(await authApi.changePassword(currentPassword, newPassword));
  }, []);

  const value = useMemo(
    () => ({ user, isLoading, portalRole, login, logout, changePassword }),
    [changePassword, isLoading, login, logout, portalRole, user],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) throw new Error("useAuth must be used within AuthProvider.");
  return context;
}
