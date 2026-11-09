import { EstimateCreate, EstimateSummary } from "./estimates";
import { apiFetch } from "./client";

export type EstimateWorkspaceSaveRequest = {
  project_id: string;
  tender_id?: string | null;
  status: string;
  estimate: EstimateCreate;
  summary?: EstimateSummary | null;
};

export type EstimateWorkspaceRead = {
  id: string;
  project_id: string;
  tender_id?: string | null;
  status: string;
  total_amount?: number | null;
  summary_text?: string | null;
  estimate: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type EstimateWorkspaceList = {
  items: EstimateWorkspaceRead[];
  total: number;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await apiFetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) throw new Error(`Request failed with ${response.status}`);
  return response.json() as Promise<T>;
}

export const estimateWorkspaceApi = {
  save: (payload: EstimateWorkspaceSaveRequest) => request<EstimateWorkspaceRead>("/estimates/workspace", { method: "POST", body: JSON.stringify(payload) }),
  listForProject: (projectId: string) => request<EstimateWorkspaceList>(`/estimates/workspace/project/${projectId}`),
  get: (workspaceId: string) => request<EstimateWorkspaceRead>(`/estimates/workspace/${workspaceId}`),
};
