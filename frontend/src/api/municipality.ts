import { apiFetch } from "./client";

export type RequirementCategory =
  | "approved_materials"
  | "testing"
  | "compaction"
  | "restoration"
  | "traffic_control"
  | "esc"
  | "permits"
  | "inspections"
  | "documentation";

export type CostImpact = "low" | "medium" | "high";
export type ProjectScope = "water" | "sanitary" | "storm" | "roadworks" | "asphalt" | "concrete" | "traffic" | "landscape" | "earthworks";

export type MunicipalityCheckRequest = {
  municipality: string;
  project_scopes: ProjectScope[];
};

export type MunicipalityRequirement = {
  municipality: string;
  category: RequirementCategory;
  title: string;
  description: string;
  scopes: ProjectScope[];
  cost_impact: CostImpact;
  estimating_note: string;
  rfq_note?: string | null;
};

export type MunicipalityCheckResponse = {
  municipality: string;
  project_scopes: ProjectScope[];
  requirement_count: number;
  high_impact_count: number;
  requirements: MunicipalityRequirement[];
  warnings: string[];
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await apiFetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });
  if (!response.ok) throw new Error(`Request failed with ${response.status}`);
  return response.json() as Promise<T>;
}

export const municipalityApi = {
  check: (payload: MunicipalityCheckRequest) =>
    request<MunicipalityCheckResponse>("/municipality/check", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
