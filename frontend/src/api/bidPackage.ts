export type BidPackageSection =
  | "executive_summary"
  | "scope_of_work"
  | "assumptions"
  | "exclusions"
  | "risks"
  | "municipality_requirements"
  | "quantities"
  | "rfq_status"
  | "supplier_coverage"
  | "documents";

export type ReadinessStatus = "ready" | "needs_review" | "missing";

export type BidPackageInputItem = {
  section: BidPackageSection;
  title: string;
  status: ReadinessStatus;
  content?: string | null;
  source: string;
};

export type BidPackageGenerateRequest = {
  project_name: string;
  municipality?: string | null;
  bid_due_date?: string | null;
  estimated_price?: number | null;
  items: BidPackageInputItem[];
};

export type BidPackageChecklistItem = {
  section: BidPackageSection;
  title: string;
  status: ReadinessStatus;
  note: string;
};

export type BidPackageSummary = {
  project_name: string;
  municipality?: string | null;
  bid_due_date?: string | null;
  estimated_price?: number | null;
  readiness_score: number;
  ready_count: number;
  needs_review_count: number;
  missing_count: number;
};

export type BidPackageGenerateResponse = {
  summary: BidPackageSummary;
  executive_summary: string;
  scope_of_work: string[];
  assumptions: string[];
  exclusions: string[];
  risks: string[];
  checklist: BidPackageChecklistItem[];
  missing_items: string[];
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

export const bidPackageApi = {
  generate: (payload: BidPackageGenerateRequest) =>
    request<BidPackageGenerateResponse>("/bid-package/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
