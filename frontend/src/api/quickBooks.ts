import { apiFetch } from "./client";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type QuickBooksStatus = {
  enabled: boolean;
  configured: boolean;
  connected: boolean;
  status: string;
  environment: "sandbox";
  required_scope: string;
  realm_id: string | null;
  company_name: string | null;
  legal_name: string | null;
  last_verified_at: string | null;
  last_error: string | null;
};

async function read<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `QuickBooks request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const quickBooksApi = {
  status: () =>
    apiFetch(`${API_BASE_URL}/finance/quickbooks/status`).then(read<QuickBooksStatus>),
  startOAuth: () =>
    apiFetch(`${API_BASE_URL}/finance/quickbooks/oauth/start`, { method: "POST" }).then(
      read<{ authorization_url: string }>,
    ),
  disconnect: () =>
    apiFetch(`${API_BASE_URL}/finance/quickbooks/disconnect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirmed: true }),
    }).then(read<QuickBooksStatus>),
};
