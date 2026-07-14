import { apiFetch } from "./client";

export type AuthUser = {
  id: string;
  email: string;
  display_name: string;
  role: "admin" | "operations_manager" | "estimator" | "viewer";
  is_active: boolean;
  password_reset_required: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
};

type AuthStatus = {
  authentication: "authenticated";
  user: AuthUser;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function readAuthResponse(response: Response): Promise<AuthStatus> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Authentication failed with ${response.status}`);
  }
  return response.json() as Promise<AuthStatus>;
}

export const authApi = {
  me: async (): Promise<AuthUser | null> => {
    const response = await apiFetch(`${API_BASE_URL}/auth/me`);
    if (response.status === 401) return null;
    return (await readAuthResponse(response)).user;
  },
  login: async (email: string, password: string): Promise<AuthUser> => {
    const response = await apiFetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    return (await readAuthResponse(response)).user;
  },
  logout: async (): Promise<void> => {
    const response = await apiFetch(`${API_BASE_URL}/auth/logout`, { method: "POST" });
    if (!response.ok && response.status !== 401) {
      throw new Error(`Logout failed with ${response.status}`);
    }
  },
  changePassword: async (currentPassword: string, newPassword: string): Promise<AuthUser> => {
    const response = await apiFetch(`${API_BASE_URL}/auth/change-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
    return (await readAuthResponse(response)).user;
  },
};
