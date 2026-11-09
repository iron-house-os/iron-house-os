import { PropsWithChildren, createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { AuthUser, authApi } from "../api/auth";
import { AUTH_SESSION_EXPIRED_EVENT } from "../api/client";
import { fieldOperationsApi } from "../api/fieldOperations";

export type PortalRole = "employee" | "operator" | "foreman" | "management" | null;

export function workforceEntryRole(role: PortalRole): PortalRole {
  return role === "operator" ? "employee" : role;
}

type AuthContextValue = {
  user: AuthUser | null;
  isLoading: boolean;
  portalRole: PortalRole;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);
const DRAFT_RECOVERY_PREFIX = "ihos:draft-recovery:";
const DRAFT_RECOVERY_OWNER_KEY = "ihos:draft-recovery-owner";

function clearLocalDraftRecovery() {
  for (let index = window.localStorage.length - 1; index >= 0; index -= 1) {
    const key = window.localStorage.key(index);
    if (key?.startsWith(DRAFT_RECOVERY_PREFIX)) window.localStorage.removeItem(key);
  }
  window.localStorage.removeItem(DRAFT_RECOVERY_OWNER_KEY);
}

function bindLocalDraftRecovery(account: AuthUser) {
  const existingOwner = window.localStorage.getItem(DRAFT_RECOVERY_OWNER_KEY);
  if (existingOwner && existingOwner !== account.id) clearLocalDraftRecovery();
  window.localStorage.setItem(DRAFT_RECOVERY_OWNER_KEY, account.id);
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [portalRole, setPortalRole] = useState<PortalRole>(null);

  const resolvePortalRole = useCallback(async (account: AuthUser | null) => {
    if (!account) { setPortalRole(null); return; }
    if (account.role !== "viewer") { setPortalRole("management"); return; }
    try {
      const field = await fieldOperationsApi.bootstrap();
      const resolved = field.employees.find((item) => item.email.toLowerCase() === account.email.toLowerCase())?.portal_role ?? "employee";
      setPortalRole(workforceEntryRole(resolved));
    } catch { setPortalRole("employee"); }
  }, []);

  useEffect(() => {
    let active = true;
    authApi
      .me()
      .then((account) => {
        if (active) {
          if (account) bindLocalDraftRecovery(account);
          else clearLocalDraftRecovery();
          setUser(account);
          return resolvePortalRole(account);
        }
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
    const expireSession = () => {
      clearLocalDraftRecovery();
      setUser(null);
    };
    window.addEventListener(AUTH_SESSION_EXPIRED_EVENT, expireSession);
    return () => window.removeEventListener(AUTH_SESSION_EXPIRED_EVENT, expireSession);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const account = await authApi.login(email, password);
    bindLocalDraftRecovery(account);
    setUser(account);
    await resolvePortalRole(account);
  }, [resolvePortalRole]);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      clearLocalDraftRecovery();
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
