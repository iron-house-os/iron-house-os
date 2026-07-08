export type ReadinessItem = {
  label: string;
  status: string;
  detail: string;
  priority: number;
};

export type ProjectReadinessResponse = {
  project_id: string;
  readiness_score: number;
  status: string;
  items: ReadinessItem[];
  blockers: string[];
  next_actions: string[];
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) throw new Error(`Request failed with ${response.status}`);
  return response.json() as Promise<T>;
}

export const projectReadinessApi = {
  get: (projectId: string) => request<ProjectReadinessResponse>(`/projects/${projectId}/readiness`),
};
