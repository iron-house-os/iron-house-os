import { apiFetch } from "./client";

export type EquipmentStatus = "available" | "reserved" | "in_use" | "maintenance" | "retired";

export type Equipment = {
  id: string;
  name: string;
  equipment_type: string | null;
  identifier: string | null;
  status: EquipmentStatus;
  hourly_rate: number | null;
  created_at: string;
  updated_at: string;
};

export type EquipmentCreate = {
  name: string;
  equipment_type?: string;
  identifier?: string;
  status?: EquipmentStatus;
  hourly_rate?: number | null;
};

export const equipmentStatuses: EquipmentStatus[] = [
  "available",
  "reserved",
  "in_use",
  "maintenance",
  "retired",
];

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await apiFetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const equipmentApi = {
  list: (status?: EquipmentStatus | "") =>
    request<{ items: Equipment[]; total: number }>(`/equipment${status ? `?status=${status}` : ""}`),
  create: (payload: EquipmentCreate) =>
    request<Equipment>("/equipment", { method: "POST", body: JSON.stringify(payload) }),
  update: (id: string, payload: Partial<EquipmentCreate>) =>
    request<Equipment>(`/equipment/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
};
