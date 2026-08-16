import { apiFetch } from "./client";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const orientationTopicCodes = [
  "supervisor_contact", "rights_and_responsibilities", "workplace_safety_rules", "workplace_hazards",
  "working_alone", "violence_prevention", "personal_protective_equipment", "first_aid",
  "emergency_procedures", "task_instruction_and_demonstration", "occupational_health_and_safety_program",
  "whmis", "committee_or_representative",
] as const;

export type OnboardingRecord = { id: string; legal_first_name: string; legal_last_name: string; category: string; position: string; status: string; primary_location: string | null };
export type DeploymentStatus = { status: "Blocked" | "Supervised work only" | "Ready"; blockers: string[]; latest_company_orientation_id: string | null; latest_site_orientation_id: string | null };
export type OrientationPayload = { scope: "company" | "site"; site_name: string | null; trigger: string; orientation_date: string; instructor_name: string; supervisor_name: string; document_version: string; competency_result: string; ppe_verified: boolean; qualifications_verified: boolean; worker_acknowledged: boolean; worker_acknowledged_at: string | null; supporting_document_ids: string[]; notes: string | null; topics: Array<{ code: string; applicability: string; evidence: string | null; not_applicable_basis: string | null }> };

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await apiFetch(`${API_BASE_URL}${path}`, { headers: { "Content-Type": "application/json", ...options?.headers }, ...options });
  if (!response.ok) { const body = await response.json().catch(() => null) as { detail?: string } | null; throw new Error(body?.detail ?? "Onboarding request failed."); }
  return response.json() as Promise<T>;
}

export const employeeOnboardingApi = {
  list: () => request<{ items: OnboardingRecord[]; total: number }>("/employee-onboarding"),
  deploymentStatus: (id: string) => request<DeploymentStatus>(`/employee-onboarding/${id}/deployment-status`),
  createOrientation: (id: string, payload: OrientationPayload) => request(`/employee-onboarding/${id}/orientations`, { method: "POST", body: JSON.stringify(payload) }),
};
