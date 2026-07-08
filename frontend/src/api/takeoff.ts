export type QuantityCategory = "pipe" | "structures" | "asphalt" | "concrete" | "earthworks" | "landscape" | "traffic" | "misc";
export type QuantitySource = "manual" | "drawing_intelligence" | "ocr" | "import" | "estimate_override";
export type QuantityUnit = "LS" | "EA" | "m" | "m2" | "m3" | "t" | "hr" | "day";

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

export const takeoffApi = {
  summarize: (payload: QuantityRegisterRequest) =>
    request<QuantityRegisterResponse>("/takeoff/summarize", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
