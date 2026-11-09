import { apiFetch } from "./client";

export type QuantityCategory = "pipe" | "structures" | "asphalt" | "concrete" | "earthworks" | "landscape" | "traffic" | "misc";
export type QuantitySource = "manual" | "drawing_intelligence" | "ocr" | "import" | "estimate_override" | "takeoff_engine";
export type QuantityUnit = "LS" | "EA" | "m" | "m2" | "m3" | "t" | "hr" | "day";
export type TakeoffMethod = "manual" | "scale_measure" | "sheet_count" | "area_trace" | "linear_trace" | "allowance" | "imported";
export type ReadinessStatus = "ready" | "review" | "blocked";

export type QuantityItem = {
  code?: string | null;
  description: string;
  category: QuantityCategory;
  quantity: number;
  unit: QuantityUnit;
  source: QuantitySource;
  confidence: number;
  estimate_ready: boolean;
  drawing_reference?: string | null;
  notes?: string | null;
  takeoff_method?: TakeoffMethod;
  scale?: string | null;
  revision?: string | null;
};

export type DrawingSheetInput = {
  sheet_number: string;
  title: string;
  discipline?: string | null;
  scale?: string | null;
  revision?: string | null;
  notes?: string | null;
};

export type TakeoffExtractionRule = {
  category: QuantityCategory;
  description: string;
  unit: QuantityUnit;
  method: TakeoffMethod;
  drawing_reference?: string | null;
  measured_value: number;
  multiplier: number;
  waste_factor: number;
  confidence: number;
  notes?: string | null;
};

export type TakeoffEngineRequest = {
  project_name?: string | null;
  project_id?: string | null;
  drawing_set_name?: string | null;
  sheets: DrawingSheetInput[];
  extraction_rules: TakeoffExtractionRule[];
  manual_items: QuantityItem[];
};

export type QuantityRegisterRequest = {
  project_name?: string | null;
  project_id?: string | null;
  items: QuantityItem[];
};

export type QuantitySummaryLine = {
  category: QuantityCategory;
  unit: QuantityUnit;
  total_quantity: number;
  item_count: number;
  estimate_ready_count: number;
};

export type EstimateReadyItem = {
  code?: string | null;
  description: string;
  category: QuantityCategory;
  quantity: number;
  unit: QuantityUnit;
  source: QuantitySource;
  confidence: number;
  drawing_reference?: string | null;
  notes?: string | null;
  takeoff_method?: TakeoffMethod;
  scale?: string | null;
  revision?: string | null;
};

export type QuantityRegisterResponse = {
  project_name?: string | null;
  project_id?: string | null;
  item_count: number;
  estimate_ready_count: number;
  low_confidence_count: number;
  summaries: QuantitySummaryLine[];
  estimate_ready_items: EstimateReadyItem[];
  warnings: string[];
};

export type TakeoffReadinessCheck = {
  label: string;
  status: ReadinessStatus;
  detail: string;
};

export type TakeoffEngineResponse = {
  project_name?: string | null;
  project_id?: string | null;
  drawing_set_name?: string | null;
  sheets_reviewed: number;
  generated_items: QuantityItem[];
  quantity_register: QuantityRegisterResponse;
  readiness_checks: TakeoffReadinessCheck[];
  estimating_handoff_items: EstimateReadyItem[];
  assumptions: string[];
  conflicts: string[];
  next_actions: string[];
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

export const takeoffApi = {
  summarize: (payload: QuantityRegisterRequest) =>
    request<QuantityRegisterResponse>("/takeoff/summarize", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  runEngine: (payload: TakeoffEngineRequest) =>
    request<TakeoffEngineResponse>("/takeoff/engine", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
