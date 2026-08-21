import { apiFetch } from "./client";

export type WorkflowType =
  | "customer_quote"
  | "estimate"
  | "purchase_order_request"
  | "supplier_quote_comparison";

export type WorkflowDraft = {
  id: string;
  owner_account_id: string;
  project_id: string | null;
  workflow_type: WorkflowType;
  title: string;
  payload: Record<string, unknown>;
  schema_version: number;
  revision: number;
  status: "active" | "cancelled" | "completed";
  last_saved_at: string;
  created_at: string;
  updated_at: string;
};

export type WorkflowDraftList = { items: WorkflowDraft[]; total: number };

const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await apiFetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    const error = new Error(body?.detail ?? `Draft request failed with ${response.status}`);
    Object.assign(error, { status: response.status });
    throw error;
  }
  return response.json() as Promise<T>;
}

export const workflowDraftsApi = {
  list: () => request<WorkflowDraftList>("/workflow-drafts"),
  get: (draftId: string) => request<WorkflowDraft>(`/workflow-drafts/${draftId}`),
  create: (payload: {
    workflow_type: WorkflowType;
    title: string;
    payload: Record<string, unknown>;
    project_id?: string | null;
    schema_version?: number;
  }) => request<WorkflowDraft>("/workflow-drafts", {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  update: (draftId: string, payload: {
    expected_revision: number;
    title: string;
    payload: Record<string, unknown>;
    project_id?: string | null;
    schema_version?: number;
  }) => request<WorkflowDraft>(`/workflow-drafts/${draftId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }),
  cancel: (draftId: string, expectedRevision: number) =>
    request<WorkflowDraft>(`/workflow-drafts/${draftId}/cancel`, {
      method: "POST",
      body: JSON.stringify({ expected_revision: expectedRevision }),
    }),
  complete: (draftId: string, expectedRevision: number) =>
    request<WorkflowDraft>(`/workflow-drafts/${draftId}/complete`, {
      method: "POST",
      body: JSON.stringify({ expected_revision: expectedRevision }),
    }),
};
