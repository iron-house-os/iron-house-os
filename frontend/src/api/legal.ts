import { apiFetch } from "./client";

export type LegalMatter = {
  id: string; title: string; matter_type: string; project_name: string | null; counterparty: string | null;
  description: string; status: string; risk_level: string; confidentiality: string; jurisdiction: string;
  assigned_specialists: string[]; created_by: string; reviewed_by: string | null; reviewed_at: string | null;
  created_at: string; updated_at: string;
};
export type LegalAnalysis = {
  id: string; executive_summary: string; draft_text: string | null; status: string; specialist_keys: string[];
  issues: Array<{ issue?: string; risk?: string; reasoning?: string; source_ids?: string[] }>;
  recommendations: Array<{ action?: string; owner?: string; urgency?: string; source_ids?: string[] }>;
  questions_for_counsel: string[]; source_ids: string[]; disclaimer: string; created_at: string;
};
export type LegalDeadline = {
  id: string; matter_id: string; title: string; due_date: string; source_basis: string; status: string;
  created_by: string; verified_by: string | null; verified_at: string | null; evidence_reference: string | null;
};
export type LegalMatterDetail = LegalMatter & { analyses: LegalAnalysis[]; deadlines: LegalDeadline[] };
export type LegalDashboard = {
  enabled: boolean; configured: boolean; mode: string; matters: LegalMatter[];
  specialists: Array<{ key: string; name: string; mandate: string }>;
  authorities: Array<{ id: string; title: string; url: string; status: string; jurisdiction: string }>;
  candidate_deadline_count: number;
};

const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(`${BASE}/legal${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(body?.detail ?? "Legal control request failed.");
  }
  return response.json() as Promise<T>;
}

export const legalApi = {
  dashboard: () => request<LegalDashboard>("/dashboard"),
  matter: (id: string) => request<LegalMatterDetail>(`/matters/${id}`),
  createMatter: (payload: Record<string, unknown>) =>
    request<LegalMatter>("/matters", { method: "POST", body: JSON.stringify(payload) }),
  analyse: (id: string, question = "") =>
    request<LegalAnalysis>(`/matters/${id}/analyse`, { method: "POST", body: JSON.stringify({ question: question || null }) }),
  createDeadline: (id: string, payload: Record<string, unknown>) =>
    request<LegalDeadline>(`/matters/${id}/deadlines`, { method: "POST", body: JSON.stringify(payload) }),
  verifyDeadline: (id: string, evidence_reference: string) =>
    request<LegalDeadline>(`/deadlines/${id}/verify`, { method: "POST", body: JSON.stringify({ evidence_reference }) }),
};
