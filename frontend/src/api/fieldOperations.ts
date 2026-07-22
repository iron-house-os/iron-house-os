import { apiFetch } from "./client";

export type SelectRecord = { id: string; name: string; [key: string]: unknown };
export type Employee = {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  role: string | null;
  phone: string | null;
  address: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  emergency_contact_relationship: string | null;
  hire_date: string | null;
  portal_role: "employee" | "operator" | "foreman" | "management";
  notes: string | null;
  status: string;
};
export type Vehicle = SelectRecord & {
  unit_number: string;
  assigned_driver_name: string | null;
  make: string | null;
  model: string | null;
  current_km: number;
  next_service_km: number | null;
  next_service_date: string | null;
  status: string;
  service_status: "current" | "due_soon" | "overdue";
};
export type FieldRecord = {
  id: string;
  record_type: string;
  project_id: string | null;
  employee_id: string | null;
  equipment_id: string | null;
  supplier_id: string | null;
  cost_code: string | null;
  work_date: string;
  title: string;
  status: string;
  severity: "none" | "low" | "medium" | "high" | "critical";
  details: Record<string, unknown>;
  document_ids: string[];
  signatures: Array<Record<string, string>>;
  alert_recipients: string[];
  submitted_by: string | null;
};
export type FieldOperationsBootstrap = {
  employees: Employee[];
  projects: SelectRecord[];
  suppliers: SelectRecord[];
  equipment: SelectRecord[];
  cost_codes: Array<{ code: string; name: string }>;
  job_workbooks: Array<{ id: string; project_id: string; status: string; created_at: string; line_count: number }>;
  production_items: Array<{
    line_key: string;
    workbook_id: string;
    project_id: string;
    cost_code: string | null;
    description: string;
    unit: string;
    estimated_quantity: number;
    installed_quantity: number;
    remaining_quantity: number;
    percent_complete: number;
    materials: Array<Record<string, unknown>>;
  }>;
  material_types: Array<{ code: string; name: string }>;
  material_movement_summary: Array<{
    project_id: string | null;
    direction: "imported" | "exported";
    material_code: string;
    material_type: string;
    loads: number;
    total_tonnes: number;
  }>;
  milestone_catalog: Array<{
    id: string;
    track: "civil" | "operator";
    name: string;
    minimum_months: number;
    practical: string[];
    written_questions: Array<{ id: string; prompt: string; options: string[] }>;
  }>;
  milestone_recognitions: Array<{
    record_id: string;
    employee_id: string;
    employee_name: string;
    milestone_name: string;
    approved_at: string;
    reward_type: string;
    reward_description: string | null;
  }>;
  paperwork_recognitions: Array<{ employee_id: string; employee_name: string; on_time_days: number }>;
  vehicles: Vehicle[];
  vehicle_logs: Array<Record<string, unknown>>;
  time_entries: Array<Record<string, unknown>>;
  records: FieldRecord[];
  certifications: Array<Record<string, unknown>>;
  alerts: Array<{ type: string; severity: string; title: string; recipients: string[] }>;
  toolbox_talk: {
    week_of: string;
    title: string;
    summary: string;
    discussion_points: string[];
    source_name: string;
    source_url: string;
  };
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await apiFetch(API_BASE_URL + path, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(body?.detail ?? "Request failed with " + response.status);
  }
  return response.json() as Promise<T>;
}

export const fieldOperationsApi = {
  bootstrap: () => request<FieldOperationsBootstrap>("/field-operations/bootstrap"),
  createVehicleLog: (payload: Record<string, unknown>) =>
    request("/field-operations/vehicle-logs", { method: "POST", body: JSON.stringify(payload) }),
  updateVehicle: (id: string, payload: Record<string, unknown>) =>
    request("/field-operations/vehicles/" + id, { method: "PATCH", body: JSON.stringify(payload) }),
  createTimeEntry: (payload: Record<string, unknown>) =>
    request("/field-operations/time-entries", { method: "POST", body: JSON.stringify(payload) }),
  createRecord: (payload: Record<string, unknown>) =>
    request<FieldRecord>("/field-operations/records", { method: "POST", body: JSON.stringify(payload) }),
  signRecord: (id: string, payload: Record<string, unknown>) =>
    request<FieldRecord>("/field-operations/records/" + id + "/sign", { method: "POST", body: JSON.stringify(payload) }),
  decideMilestone: (id: string, payload: Record<string, unknown>) =>
    request<FieldRecord>("/field-operations/records/" + id + "/milestone-decision", { method: "POST", body: JSON.stringify(payload) }),
  createEmployee: (payload: Record<string, unknown>) =>
    request("/field-operations/employees", { method: "POST", body: JSON.stringify(payload) }),
  createCertification: (payload: Record<string, unknown>) =>
    request("/field-operations/certifications", { method: "POST", body: JSON.stringify(payload) }),
};
