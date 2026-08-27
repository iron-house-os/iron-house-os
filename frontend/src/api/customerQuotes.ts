import { apiFetch } from "./client";

export type CustomerQuoteStatus = "draft" | "sent" | "accepted" | "declined" | "expired";
export type CustomerQuoteIssueStatus = "draft" | "ready_for_review" | "approved_for_issue" | "issued";

export type CustomerQuoteLineItem = {
  description: string;
  quantity: string;
  unit: string;
  unit_price: string;
  amount?: string;
};

export type CustomerQuote = {
  id: string;
  project_id: string;
  source_estimate_workspace_id: string | null;
  project_name: string;
  quote_number: string;
  customer_name: string;
  customer_email: string | null;
  customer_phone: string | null;
  site_address: string | null;
  scope_summary: string;
  line_items: CustomerQuoteLineItem[];
  assumptions: string[];
  exclusions: string[];
  subtotal: string;
  gst_rate: string;
  gst: string;
  total: string;
  quote_date: string;
  valid_until: string | null;
  status: CustomerQuoteStatus;
  record_revision: number;
  notes: string | null;
  created_by: string;
  sent_at: string | null;
  issue_status: CustomerQuoteIssueStatus;
  approved_revision: number | null;
  approved_at: string | null;
  approved_by: string | null;
  issued_at: string | null;
  issued_by: string | null;
  issuance_method: string | null;
  issuance_reference: string | null;
  accepted_at: string | null;
  accepted_by: string | null;
  acceptance_reference: string | null;
  acceptance_note: string | null;
  closed_at: string | null;
  job_number: string | null;
  created_at: string;
  updated_at: string;
};

export type CustomerQuoteInput = {
  project_name: string;
  customer_name: string;
  customer_email?: string | null;
  customer_phone?: string | null;
  site_address?: string | null;
  scope_summary: string;
  line_items: CustomerQuoteLineItem[];
  assumptions: string[];
  exclusions: string[];
  gst_rate: string;
  quote_date: string;
  valid_until?: string | null;
  notes?: string | null;
};

const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await apiFetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as {
      detail?: string;
      error?: { message?: string };
    } | null;
    throw new Error(
      body?.detail
      ?? body?.error?.message
      ?? `Customer quote request failed with ${response.status}`,
    );
  }
  return response.json() as Promise<T>;
}

export const customerQuotesApi = {
  list: () => request<{ items: CustomerQuote[]; total: number }>("/customer-quotes"),
  pdfUrl: (quoteId: string) => `${BASE}/customer-quotes/${quoteId}/pdf`,
  create: (payload: CustomerQuoteInput) => request<CustomerQuote>("/customer-quotes", {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  fromEstimate: (workspaceId: string) =>
    request<CustomerQuote>(`/customer-quotes/from-estimate/${workspaceId}`, { method: "POST" }),
  update: (quoteId: string, revision: number, payload: CustomerQuoteInput) =>
    request<CustomerQuote>(`/customer-quotes/${quoteId}`, {
      method: "PATCH",
      body: JSON.stringify({ ...payload, expected_revision: revision }),
    }),
  status: (quoteId: string, revision: number, status: "sent" | "declined" | "expired", note?: string) =>
    request<CustomerQuote>(`/customer-quotes/${quoteId}/status`, {
      method: "POST",
      body: JSON.stringify({ expected_revision: revision, status, note: note || null }),
    }),
  issueStatus: (
    quoteId: string,
    revision: number,
    status: CustomerQuoteIssueStatus,
    issuanceMethod?: string,
    issuanceReference?: string,
  ) => request<CustomerQuote>(`/customer-quotes/${quoteId}/issue-status`, {
    method: "POST",
    body: JSON.stringify({
      expected_revision: revision,
      status,
      issuance_method: issuanceMethod || null,
      issuance_reference: issuanceReference || null,
    }),
  }),
  accept: (quoteId: string, revision: number, acceptanceReference: string, acceptanceNote?: string) =>
    request<CustomerQuote>(`/customer-quotes/${quoteId}/accept`, {
      method: "POST",
      body: JSON.stringify({
        expected_revision: revision,
        acceptance_reference: acceptanceReference,
        acceptance_note: acceptanceNote || null,
      }),
    }),
};
