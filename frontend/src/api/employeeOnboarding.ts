import { apiFetch } from "./client";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const orientationTopicCodes = [
  "supervisor_contact", "rights_and_responsibilities", "workplace_safety_rules", "workplace_hazards",
  "working_alone", "violence_prevention", "personal_protective_equipment", "first_aid",
  "emergency_procedures", "task_instruction_and_demonstration", "occupational_health_and_safety_program",
  "whmis", "committee_or_representative",
] as const;

export const requiredOnboardingItems = [
  ["personal_information", "Personal information"],
  ["emergency_contact", "Emergency contact"],
  ["address", "Address"],
  ["payroll", "Payroll and direct deposit"],
  ["tax_forms", "2026 federal and British Columbia TD1 tax forms"],
  ["employment_agreements", "Employment agreements and policies"],
  ["certifications", "Licences, tickets, and certifications"],
  ["ppe_requirements", "PPE requirements and sizing"],
  ["electronic_signature", "Electronic acknowledgement"],
] as const;

export type OnboardingStatus =
  | "draft"
  | "invitation_sent"
  | "invitation_opened"
  | "in_progress"
  | "submitted"
  | "corrections_required"
  | "approved"
  | "active"
  | "invitation_expired"
  | "cancelled";

export type EmploymentCategory = "field_staff" | "office_staff";

export type OnboardingRecord = {
  id: string;
  legal_first_name: string;
  legal_last_name: string;
  preferred_name: string | null;
  personal_email: string;
  mobile_phone: string | null;
  category: EmploymentCategory;
  position: string;
  supervisor_id: string | null;
  employment_type: string;
  start_date: string;
  primary_location: string | null;
  onboarding_package: string | null;
  status: OnboardingStatus;
  completion_percent: number;
  missing_items: string[];
  reviewer_id: string | null;
  correction_note: string | null;
  invitation_expires_at: string | null;
  invited_at: string | null;
  submitted_at: string | null;
  approved_at: string | null;
  activated_at: string | null;
  created_at: string;
  updated_at: string;
};

export type PositionOption = {
  value: string;
  label: string;
  category: EmploymentCategory;
  level: number;
};

export type DeploymentStatus = {
  status: "Blocked" | "Supervised work only" | "Ready";
  blockers: string[];
  latest_company_orientation_id: string | null;
  latest_site_orientation_id: string | null;
};

export type OrientationPayload = {
  scope: "company" | "site";
  site_name: string | null;
  trigger: string;
  orientation_date: string;
  instructor_name: string;
  supervisor_name: string;
  document_version: string;
  competency_result: string;
  ppe_verified: boolean;
  qualifications_verified: boolean;
  worker_acknowledged: boolean;
  worker_acknowledged_at: string | null;
  supporting_document_ids: string[];
  notes: string | null;
  topics: Array<{
    code: string;
    applicability: string;
    evidence: string | null;
    not_applicable_basis: string | null;
  }>;
};

export type OnboardingCreatePayload = {
  legal_first_name: string;
  legal_last_name: string;
  preferred_name: string | null;
  personal_email: string;
  mobile_phone: string | null;
  category: EmploymentCategory;
  position: string;
  supervisor_id: string | null;
  employment_type: string;
  start_date: string;
  primary_location: string | null;
  onboarding_package: string | null;
};

export type Invitation = {
  onboarding_id: string;
  invite_url: string;
  expires_at: string;
};

export type PortalCertification = {
  name: string;
  certificate_number: string | null;
  issuer: string | null;
  expiry_date: string | null;
};

export type PortalPacket = {
  personal_information: {
    preferred_name: string | null;
    mobile_phone: string;
    date_of_birth: string;
  } | null;
  address: {
    street_address: string;
    unit: string | null;
    city: string;
    province: string;
    postal_code: string;
    country: string;
  } | null;
  emergency_contact: {
    full_name: string;
    relationship: string;
    primary_phone: string;
    alternate_phone: string | null;
  } | null;
  payroll: {
    payment_method: "direct_deposit" | "cheque";
    account_holder_name: string | null;
    institution_number: string | null;
    transit_number: string | null;
    account_number: string | null;
    direct_deposit_authorized: boolean;
  } | null;
  tax_forms: {
    form_year: 2026;
    social_insurance_number: string;
    country_of_permanent_residence: string;
    federal_claim_amounts: string[];
    bc_claim_amounts: string[];
    federal_more_than_one_employer: boolean;
    federal_total_income_less_than_claim: boolean;
    non_resident_world_income_90_percent_or_more: boolean | null;
    additional_tax_per_payment: string;
    bc_more_than_one_employer: boolean;
    bc_total_income_less_than_claim: boolean;
    federal_certified: boolean;
    bc_certified: boolean;
  } | null;
  employment_agreements: {
    employment_terms_reviewed: boolean;
    company_policies_reviewed: boolean;
    privacy_notice_reviewed: boolean;
    purchase_receipt_standard_reviewed: boolean;
    questions_resolved: boolean;
  } | null;
  certifications: {
    none_to_report: boolean;
    certifications: PortalCertification[];
  } | null;
  ppe_requirements: {
    site_ppe_required: boolean;
    boot_size: string | null;
    glove_size: string | null;
    shirt_size: string | null;
    trouser_size: string | null;
    prescription_safety_glasses: boolean;
    respirator_fit_test_required: boolean;
    notes: string | null;
  } | null;
  signature_name: string | null;
  signed_at: string | null;
};

export type PortalOnboarding = {
  onboarding: OnboardingRecord;
  packet: PortalPacket;
};

export type PortalActivation = {
  onboarding: OnboardingRecord;
  employee_id: string;
  account_id: string;
  username: string;
  temporary_password: string;
  portal_role: "employee" | "operator" | "foreman";
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await apiFetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(body?.detail ?? "Onboarding request failed.");
  }
  return response.json() as Promise<T>;
}

export const employeeOnboardingApi = {
  list: () => request<{ items: OnboardingRecord[]; total: number }>("/employee-onboarding"),
  positions: () => request<PositionOption[]>("/employee-onboarding/positions"),
  create: (payload: OnboardingCreatePayload) =>
    request<OnboardingRecord>("/employee-onboarding", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  invite: (id: string) =>
    request<Invitation>(`/employee-onboarding/${id}/invite`, { method: "POST" }),
  reviewPacket: (id: string) =>
    request<PortalPacket>(`/employee-onboarding/${id}/packet`),
  revoke: (id: string) =>
    request<OnboardingRecord>(`/employee-onboarding/${id}/revoke`, { method: "POST" }),
  requestCorrections: (id: string, note: string) =>
    request<OnboardingRecord>(`/employee-onboarding/${id}/request-corrections`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  approve: (id: string) =>
    request<OnboardingRecord>(`/employee-onboarding/${id}/approve`, { method: "POST" }),
  activate: (id: string) =>
    request<PortalActivation>(`/employee-onboarding/${id}/activate`, { method: "POST" }),
  deploymentStatus: (id: string) =>
    request<DeploymentStatus>(`/employee-onboarding/${id}/deployment-status`),
  createOrientation: (id: string, payload: OrientationPayload) =>
    request(`/employee-onboarding/${id}/orientations`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  portalRecord: (token: string) =>
    request<PortalOnboarding>(`/employee-onboarding/portal/${token}`),
  savePortalProgress: (token: string, packet: PortalPacket) =>
    request<PortalOnboarding>(`/employee-onboarding/portal/${token}/progress`, {
      method: "PUT",
      body: JSON.stringify({ packet }),
    }),
  submitPortal: (token: string, packet: PortalPacket, acknowledgement: boolean, signatureName: string) =>
    request<PortalOnboarding>(`/employee-onboarding/portal/${token}/submit`, {
      method: "POST",
      body: JSON.stringify({ packet, acknowledgement, signature_name: signatureName }),
    }),
};
