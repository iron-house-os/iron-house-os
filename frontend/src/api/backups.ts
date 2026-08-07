import { apiFetch } from "./client";

export type BackupsStatus = "pending" | "processing" | "routed" | "needs_review" | "failed";
export type BackupsDetectedType = "receipt" | "supplier_invoice" | "packing_slip" | "other";
export type BackupsReviewDestination = "finance_intake" | "finance_receipts" | "finance_invoices" | "finance_packing_slips" | "backups_needs_review";
export type BackupsRoutableDestination = Exclude<BackupsReviewDestination, "finance_intake">;

export type BackupsAuditEvent = {
  id: string;
  action: string;
  actor_email: string;
  from_status: string | null;
  to_status: string | null;
  details: Record<string, unknown>;
  created_at: string;
};

export type BackupsIntake = {
  id: string;
  media_id: string;
  media_hash: string;
  uploader_id: string;
  uploader_email: string;
  uploader_role: string;
  upload_timestamp: string;
  note: string | null;
  project_hint: string | null;
  status: BackupsStatus;
  detected_type: BackupsDetectedType | null;
  confidence: number | null;
  classification_source: string | null;
  review_destination: BackupsReviewDestination | null;
  destination_type: string | null;
  destination_record_id: string | null;
  error: string | null;
  sensitive_quarantine: boolean;
  attempt_count: number;
  last_attempt_at: string | null;
  processing_started_at: string | null;
  processed_at: string | null;
  routed_at: string | null;
  failed_at: string | null;
  created_at: string;
  updated_at: string;
  audit_history: BackupsAuditEvent[];
};

export type BackupsControllerResult = {
  claimed: number;
  routed: number;
  needs_review: number;
  failed: number;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await apiFetch(API_BASE_URL + path, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as
      | { detail?: string; error?: { message?: string } }
      | null;
    throw new Error(body?.detail ?? body?.error?.message ?? "Backups request failed.");
  }
  return response.json() as Promise<T>;
}

export const backupsApi = {
  list: () => request<{ items: BackupsIntake[]; total: number }>("/backups"),
  create: (payload: { media_id: string; note?: string | null; project_hint?: string | null }) =>
    request<BackupsIntake>("/backups", { method: "POST", body: JSON.stringify(payload) }),
  route: (id: string, previousDestination: BackupsReviewDestination, destination: BackupsRoutableDestination) =>
    request<BackupsIntake>(`/backups/${id}/destination`, {
      method: "PATCH",
      body: JSON.stringify({ previous_destination: previousDestination, destination }),
    }),
  retry: (id: string) => request<BackupsIntake>(`/backups/${id}/retry`, { method: "POST" }),
  runDaily: () => request<BackupsControllerResult>("/backups/controller/daily", { method: "POST" }),
};
