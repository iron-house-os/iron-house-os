import { apiFetch } from "./client";

export type RFQAutomationInputItem = {
  category: string;
  description: string;
  quantity?: number | null;
  unit?: string | null;
  source: "quantity" | "municipality" | "estimate" | "manual";
};

export type RFQPackageDraft = {
  title: string;
  scope_summary: string;
  supplier_category_targets: string[];
  required_documents: string[];
  source_scope: string;
  priority: number;
  review_notes: string[];
};

export type RFQLinkageRequest = {
  project_id?: string | null;
  project_name?: string | null;
  municipality?: string | null;
  source_items: RFQAutomationInputItem[];
  include_default_civil_scopes: boolean;
};

export type RFQLinkageResponse = {
  project_id?: string | null;
  project_name?: string | null;
  package_count: number;
  packages: RFQPackageDraft[];
  warnings: string[];
  recommendations: unknown[];
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

export const rfqLinkageApi = {
  buildDrafts: (payload: RFQLinkageRequest) => request<RFQLinkageResponse>("/rfq-automation/linkage", { method: "POST", body: JSON.stringify(payload) }),
};
