import { apiFetch } from "./client";

export type CostCode = { code: string; name: string };
export type LabourSplit = { cost_code: string; straight_time: number; overtime: number; start_time?: string | null; end_time?: string | null };
export type LabourLine = { employee_id: string; equipment_id?: string | null; splits: LabourSplit[] };
export type EquipmentLine = { source: "owned" | "rental"; resource_id: string; vendor_id?: string | null; unit: string; notes?: string; splits: Array<{ cost_code: string; quantity: number }> };
export type MaterialLine = { description: string; vendor_id: string; cost_code: string; quantity: number; unit: string; production_quantity?: number | null; production_unit?: string | null; receipt_id?: string | null; document_id?: string | null; notes?: string };
export type DailyTimesheetPayload = { work_date: string; shift: "day" | "night"; project_id: string; project_manager_id?: string | null; supervisor_id: string; weather: string; site_conditions: string; document_ids: string[]; ticket_document_ids: string[]; labour: LabourLine[]; equipment: EquipmentLine[]; materials: MaterialLine[]; narrative: { work_completed: string; delays_issues: string; potential_change: boolean; potential_change_details: string; safety_quality_notes: string; general_comments: string } };
export type DailyTimesheet = { id: string; status: string; version: number; project_id: string; work_date: string; shift: "day" | "night"; details: Record<string, any>; document_ids: string[]; ticket_document_ids: string[]; submitted_by: string | null; created_at: string; updated_at: string };
export type DailyTimesheetBootstrap = { projects: Array<{ id: string; name: string; project_number: string; status: string }>; employees: Array<{ id: string; code: string; name: string; classification: string; portal_role: string }>; equipment: Array<{ id: string; name: string; identifier?: string; status: string }>; rentals: Array<{ id: string; name: string; project_id?: string; vendor_id?: string; status: string }>; vendors: Array<{ id: string; name: string; category?: string }>; receipts: Array<{ id: string; reference?: string; vendor_name?: string; receipt_date?: string; status: string }>; project_cost_codes: Record<string, CostCode[]>; assigned_crew: Record<string, string[]>; sheets: DailyTimesheet[]; can_approve: boolean };

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await apiFetch(API_BASE_URL + path, { headers: { "Content-Type": "application/json", ...options?.headers }, ...options });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string; error?: { message?: string } } | null;
    throw new Error(body?.detail ?? body?.error?.message ?? "Daily time sheet request failed.");
  }
  return response.json() as Promise<T>;
}

export const dailyTimesheetApi = {
  bootstrap: () => request<DailyTimesheetBootstrap>("/daily-timesheets/bootstrap"),
  save: (payload: DailyTimesheetPayload, id?: string) => request<DailyTimesheet>("/daily-timesheets" + (id ? "/" + id : ""), { method: id ? "PUT" : "POST", body: JSON.stringify(payload) }),
  submit: (id: string) => request<DailyTimesheet>(`/daily-timesheets/${id}/submit`, { method: "POST" }),
  action: (id: string, action: "approve" | "reject" | "void" | "reopen", reason?: string) => request<DailyTimesheet>(`/daily-timesheets/${id}/actions/${action}`, { method: "POST", body: JSON.stringify({ reason: reason || null }) }),
  revision: (id: string, reason: string) => request<DailyTimesheet>(`/daily-timesheets/${id}/revision`, { method: "POST", body: JSON.stringify({ reason }) }),
  post: (id: string) => request<DailyTimesheet>(`/daily-timesheets/${id}/post`, { method: "POST" }),
  exportCsv: async (id: string) => {
    const response = await apiFetch(`${API_BASE_URL}/daily-timesheets/${id}/export.csv`, { method: "POST" });
    if (!response.ok) throw new Error("Only an approved daily sheet can be exported.");
    return response.blob();
  },
  pdfUrl: (id: string) => `${API_BASE_URL}/daily-timesheets/${id}/export.pdf`,
  csvUrl: (id: string) => `${API_BASE_URL}/daily-timesheets/${id}/export.csv`,
};
