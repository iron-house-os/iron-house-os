export type ProcurementScope =
  | "pipe_supply"
  | "structures_supply"
  | "aggregate_supply"
  | "asphalt_paving"
  | "concrete_subcontract"
  | "testing"
  | "traffic_control"
  | "landscaping"
  | "earthworks_support"
  | "disposal"
  | "misc";

export type SourceSignal = "quantity" | "municipality" | "estimate" | "manual";

export type RFQAutomationInputItem = {
  category: string;
  description: string;
  quantity?: number | null;
  unit?: string | null;
  source: SourceSignal;
};

export type RFQAutomationRequest = {
  project_name?: string | null;
  municipality?: string | null;
  items: RFQAutomationInputItem[];
  include_default_civil_scopes: boolean;
};

export type RFQScopeRecommendation = {
  scope: ProcurementScope;
  title: string;
  reason: string;
  supplier_categories: string[];
  required_documents: string[];
  priority: number;
  source_signals: SourceSignal[];
  review_notes: string[];
};

export type RFQAutomationResponse = {
  project_name?: string | null;
  municipality?: string | null;
  recommendation_count: number;
  high_priority_count: number;
  recommendations: RFQScopeRecommendation[];
  warnings: string[];
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
  if (!response.ok) throw new Error(`Request failed with ${response.status}`);
  return response.json() as Promise<T>;
}

export const rfqAutomationApi = {
  recommend: (payload: RFQAutomationRequest) =>
    request<RFQAutomationResponse>("/rfq-automation/recommend", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
