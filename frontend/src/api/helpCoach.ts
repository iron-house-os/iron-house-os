import { apiFetch } from "./client";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type HelpCoachSource = {
  id: string;
  title: string;
  path: string;
};

export type HelpCoachReply = {
  answer: string;
  status: "completed" | "static_fallback" | "no_match" | "restricted";
  audience: "employee" | "foreman" | "management";
  mode: "read-only";
  sources: HelpCoachSource[];
};

export type HelpFeedbackType = "helpful" | "not_helpful" | "stuck" | "suggestion";
export type HelpImprovementStatus = "new" | "reviewing" | "planned" | "dismissed";

export type HelpFeedbackPayload = {
  feedbackType: HelpFeedbackType;
  route?: string;
  projectName?: string;
  sourceIds?: string[];
  note?: string;
};

export type HelpFeedbackReceipt = {
  recorded: boolean;
  improvement_id: string;
  status: "recorded";
  message: string;
};

export type HelpImprovement = {
  id: string;
  feedback_type: HelpFeedbackType;
  route: string;
  source_ids: string[];
  status: HelpImprovementStatus;
  evidence_count: number;
  last_seen_at: string;
  latest_note: string | null;
  latest_project_name: string | null;
  review_note: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
};

export type HelpImprovementList = {
  items: HelpImprovement[];
  total: number;
};

export type HelpFeedbackEvidence = {
  id: string;
  audience: "employee" | "foreman" | "management";
  project_name: string | null;
  note: string | null;
  created_at: string;
};

export type HelpFeedbackEvidenceList = {
  items: HelpFeedbackEvidence[];
  total: number;
};

async function read<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Help request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const helpCoachApi = {
  send: (
    message: string,
    context: { route?: string; projectName?: string },
    signal?: AbortSignal,
  ) => apiFetch(`${API_BASE_URL}/help-coach/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      route: context.route ?? "",
      project_name: context.projectName ?? "",
    }),
    signal,
  }).then((response) => read<HelpCoachReply>(response)),
  submitFeedback: (payload: HelpFeedbackPayload) => apiFetch(`${API_BASE_URL}/help-coach/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      feedback_type: payload.feedbackType,
      route: payload.route ?? "",
      project_name: payload.projectName ?? "",
      source_ids: payload.sourceIds ?? [],
      note: payload.note?.trim() || null,
    }),
  }).then((response) => read<HelpFeedbackReceipt>(response)),
  listImprovements: () => apiFetch(`${API_BASE_URL}/help-coach/improvements`)
    .then((response) => read<HelpImprovementList>(response)),
  listImprovementEvidence: (improvementId: string) => apiFetch(
    `${API_BASE_URL}/help-coach/improvements/${improvementId}/evidence`,
  ).then((response) => read<HelpFeedbackEvidenceList>(response)),
  updateImprovement: (
    improvementId: string,
    status: HelpImprovementStatus,
    reviewNote?: string,
  ) => apiFetch(`${API_BASE_URL}/help-coach/improvements/${improvementId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, review_note: reviewNote?.trim() || null }),
  }).then((response) => read<HelpImprovement>(response)),
};
