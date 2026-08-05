import { apiFetch } from "./client";

export type BackupStatus = "pending" | "processing" | "routed" | "needs_review" | "failed";
export type BackupDetectedType = "receipt" | "supplier_invoice" | "packing_slip" | "other";

export type BackupAuditEvent = {
  id: string;
  action: string;
  actor_email: string;
  from_status: string | null;
  to_status: string | null;
  detail_json: Record<string, unknown>;
  created_at: string;
};

export type BackupIntake = {
  id: string;
  media_asset_id: string;
  media_sha256: string;
  uploader_id: string;
  uploader_email: string;
  uploader_role: string;
  uploaded_at: string;
  note: string | null;
  project_hint: string | null;
  status: BackupStatus;
  detected_type: BackupDetectedType | null;
  confidence: number | null;
  destination_type: string | null;
  destination_record_id: string | null;
  error: string | null;
  sensitive_quarantine: boolean;
  classifier: string | null;
  attempt_count: number;
  audit_history: BackupAuditEvent[];
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function responseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string; error?: { message?: string } } | null;
    throw new Error(payload?.detail ?? payload?.error?.message ?? `Backups request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const backupsApi = {
  list: async () => responseJson<{ items: BackupIntake[]; total: number }>(
    await apiFetch(`${API_BASE_URL}/backups`),
  ),
  upload: async (file: File, note?: string, projectHint?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (note) form.append("note", note);
    if (projectHint) form.append("project_hint", projectHint);
    return responseJson<BackupIntake>(await apiFetch(`${API_BASE_URL}/backups`, { method: "POST", body: form }));
  },
  runDaily: async () => responseJson<{ selected: number; routed: number; needs_review: number; failed: number }>(
    await apiFetch(`${API_BASE_URL}/backups/controller/daily`, { method: "POST" }),
  ),
};
