export type ProjectStatus =
  | "opportunity"
  | "tendering"
  | "awarded"
  | "construction"
  | "completed"
  | "archived";

export type Project = {
  id: string;
  name: string;
  client_owner: string | null;
  municipality: string | null;
  project_number: string | null;
  tender_number: string | null;
  tender_source: string | null;
  tender_closing_date: string | null;
  bid_due_date: string | null;
  estimated_construction_start: string | null;
  estimated_construction_finish: string | null;
  project_address: string | null;
  latitude: number | null;
  longitude: number | null;
  contract_value: number | null;
  status: ProjectStatus;
  notes: string | null;
  metadata: Record<string, unknown>;
  supplier_ids: string[];
  created_at: string;
  updated_at: string;
};

export type ProjectList = {
  items: Project[];
  total: number;
};

export type ProjectCreatePayload = {
  name: string;
  client_owner?: string;
  municipality?: string;
  project_number?: string;
  tender_number?: string;
  tender_source?: string;
  tender_closing_date?: string;
  bid_due_date?: string;
  estimated_construction_start?: string;
  estimated_construction_finish?: string;
  project_address?: string;
  latitude?: number;
  longitude?: number;
  contract_value?: number;
  status?: ProjectStatus;
  notes?: string;
  supplier_ids?: string[];
  metadata?: Record<string, unknown>;
};

export type ProjectDashboard = {
  project_id: string;
  rfq_count: number;
  supplier_count: number;
  document_count: number;
  drawing_count: number;
  bid_status: string;
  readiness_percentage: number;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const projectStatuses: ProjectStatus[] = [
  "opportunity",
  "tendering",
  "awarded",
  "construction",
  "completed",
  "archived",
];

export const projectsApi = {
  list: (status?: string) => {
    const suffix = status ? `?status=${encodeURIComponent(status)}` : "";
    return request<ProjectList>(`/projects${suffix}`);
  },
  create: (payload: ProjectCreatePayload) =>
    request<Project>("/projects", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  detail: (id: string) => request<Project>(`/projects/${id}`),
  update: (id: string, payload: Partial<ProjectCreatePayload>) =>
    request<Project>(`/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  archive: (id: string) =>
    request<Project>(`/projects/${id}/archive`, {
      method: "POST",
    }),
  dashboard: (id: string) => request<ProjectDashboard>(`/projects/${id}/dashboard`),
};
