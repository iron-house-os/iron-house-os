import { apiFetch } from "./client";

export type FinancialEntry = { id: string; project_id: string; cost_code: string; entry_type: string; category: string; amount: number; entry_date: string; vendor_name: string | null; reference: string | null; description: string | null; status: string };
export type FinancialSummary = { project_id: string; project_name: string; contract_value: number; budget: number; committed: number; actual: number; forecast_cost: number; cost_variance: number; forecast_profit: number; forecast_margin_percent: number; entries: FinancialEntry[]; cost_codes: Array<{ cost_code: string; budget: number; committed: number; actual: number; forecast: number; variance: number }> };
export type StartupExpense = { id: string; expense_date: string; vendor_name: string; description: string; amount: number; category: string; reference: string | null; source_email: string | null; funding_source: string; owner_name: string | null; tax_treatment: string; status: string; receipt_metadata: Record<string, unknown> };
export type StartupExpenseSummary = { total_startup_costs: number; owner_loan_payable: number; reimbursed_to_owner: number; pending_review: number; approved_unreimbursed: number; entries: StartupExpense[] };
const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
async function request<T>(path: string, options?: RequestInit): Promise<T> { const response = await apiFetch(BASE + path, { headers: { "Content-Type": "application/json", ...options?.headers }, ...options }); if (!response.ok) { const body = await response.json().catch(() => null) as { detail?: string } | null; throw new Error(body?.detail ?? "Financial request failed"); } return response.json() as Promise<T>; }
export const financeApi = {
  getProject: (id: string) => request<FinancialSummary>(`/finance/projects/${id}`),
  importEstimate: (id: string) => request<FinancialSummary>(`/finance/projects/${id}/import-estimate`, { method: "POST", body: "{}" }),
  createEntry: (payload: Record<string, unknown>) => request<FinancialEntry>("/finance/entries", { method: "POST", body: JSON.stringify(payload) }),
  quickBooksUrl: (id: string) => `${BASE}/finance/projects/${id}/quickbooks.csv`,
  getStartupExpenses: () => request<StartupExpenseSummary>("/finance/startup-expenses"),
  createStartupExpense: (payload: Record<string, unknown>) => request<StartupExpense>("/finance/startup-expenses", { method: "POST", body: JSON.stringify(payload) }),
  updateStartupExpense: (id: string, payload: Record<string, unknown>) => request<StartupExpense>(`/finance/startup-expenses/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  startupQuickBooksUrl: () => `${BASE}/finance/startup-expenses/quickbooks.csv`,
};
