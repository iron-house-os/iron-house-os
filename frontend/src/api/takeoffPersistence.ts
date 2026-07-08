import { QuantityItem, QuantityRegisterResponse, TakeoffEngineResponse } from "./takeoff";

export type TakeoffSaveRequest = {
  project_id: string;
  drawing_id?: string | null;
  status: string;
  notes?: string | null;
  items: QuantityItem[];
  engine_result?: TakeoffEngineResponse | null;
  quantity_register?: QuantityRegisterResponse | null;
};

export type TakeoffRead = {
  id: string;
  project_id: string;
  drawing_id?: string | null;
  status: string;
  notes?: string | null;
  quantities: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type TakeoffList = {
  items: TakeoffRead[];
  total: number;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) throw new Error(`Request failed with ${response.status}`);
  return response.json() as Promise<T>;
}

export const takeoffPersistenceApi = {
  save: (payload: TakeoffSaveRequest) => request<TakeoffRead>("/takeoff/save", { method: "POST", body: JSON.stringify(payload) }),
  listForProject: (projectId: string) => request<TakeoffList>(`/takeoff/project/${projectId}`),
  get: (takeoffId: string) => request<TakeoffRead>(`/takeoff/${takeoffId}`),
};
