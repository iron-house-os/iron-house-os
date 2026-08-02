import { apiFetch } from "./client";

export type FinancialEntry = { id: string; project_id: string; cost_code: string; entry_type: string; category: string; amount: number; entry_date: string; vendor_name: string | null; vendor_address: string | null; reference: string | null; description: string | null; status: string };
export type FinancialSummary = { project_id: string; project_name: string; contract_value: number; budget: number; committed: number; actual: number; forecast_cost: number; cost_variance: number; forecast_profit: number; forecast_margin_percent: number; entries: FinancialEntry[]; cost_codes: Array<{ cost_code: string; budget: number; committed: number; actual: number; forecast: number; variance: number }> };
export type StartupExpense = { id: string; expense_date: string; vendor_name: string; description: string; amount: number; category: string; reference: string | null; source_email: string | null; funding_source: string; owner_name: string | null; tax_treatment: string; status: string; receipt_metadata: Record<string, unknown> };

export type ReceiptLineItem = { id: string; position: number; description: string; normalized_description: string | null; quantity: number; unit_price: number; tax: number; line_total: number; category: string; project_id: string | null; equipment_id: string | null; cost_code: string | null; overhead_category: string | null; treatment: string; confidence: number; source_region: Record<string, number> | null; flags: string[] };
export type Receipt = { id: string; status: string; submitter_email: string; media_asset_ids: string[]; vendor_id: string | null; vendor_name: string | null; vendor_address: string | null; reference: string | null; receipt_date: string | null; receipt_time: string | null; currency: string; subtotal: number | null; discounts: number; gst: number; pst: number; other_tax: number; tip: number; total: number | null; payment_method: string | null; card_brand: string | null; card_last_four: string | null; company_card_id: string | null; employee_email: string | null; treatment: string; confidence: Record<string, number>; source_regions: Record<string, Record<string, number>>; flags: string[]; duplicate_of_id: string | null; approved_by: string | null; exported_by: string | null; version: number; reconciliation_difference: number | null; is_balanced: boolean; approval_blockers: string[]; line_items: ReceiptLineItem[]; audit_history: Array<{ id: string; action: string; actor_email: string; reason: string | null; created_at: string }> };
export type ReceiptList = { items: Receipt[]; total: number };
export type ReceiptExtraction = { model: string; draft: { media_asset_ids: string[]; vendor_name: string | null; vendor_address: string | null; reference: string | null; receipt_date: string | null; receipt_time: string | null; currency: string; subtotal: number | null; discounts: number; gst: number; pst: number; other_tax: number; tip: number; total: number | null; payment_method: string | null; card_brand: string | null; card_last_four: string | null; employee_email: string | null; treatment: string; confidence: Record<string, number>; source_regions: Record<string, Record<string, number>>; flags: string[]; line_items: Array<Omit<ReceiptLineItem, "id" | "position">> } };

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
  getReceipts: (status?: string) => request<ReceiptList>("/finance/receipts" + (status ? "?receipt_status=" + encodeURIComponent(status) : "")),
  createReceipt: (payload: Record<string, unknown>) => request<Receipt>("/finance/receipts", { method: "POST", body: JSON.stringify(payload) }),
  extractReceipt: (mediaAssetIds: string[]) => request<ReceiptExtraction>("/finance/receipts/extract", { method: "POST", body: JSON.stringify({ media_asset_ids: mediaAssetIds }) }),
  updateReceipt: (id: string, payload: Record<string, unknown>) => request<Receipt>(`/finance/receipts/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  receiptAction: (id: string, action: "submit" | "approve" | "reconcile" | "void", version: number, reason: string) => request<Receipt>(`/finance/receipts/${id}/${action}`, { method: "POST", body: JSON.stringify({ version, reason }) }),
  exportReceipt: async (id: string, version: number, reason: string) => {
    const response = await apiFetch(`${BASE}/finance/receipts/${id}/export`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ version, reason }) });
    if (!response.ok) { const body = await response.json().catch(() => null) as { detail?: string } | null; throw new Error(typeof body?.detail === "string" ? body.detail : "Receipt export failed"); }
    return response.blob();
  },
};
