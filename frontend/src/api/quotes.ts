import type { EstimateLineItem } from "./estimates";

export type QuoteScopeType = "material" | "subcontract" | "trucking" | "disposal" | "equipment" | "other";

export type QuoteStatus = "requested" | "received" | "declined" | "bounced" | "selected" | "rejected";

export type SupplierQuoteCreate = {
  rfq_id?: string | null;
  rfq_package_id?: string | null;
  supplier_id?: string | null;
  supplier_name: string;
  quote_reference?: string | null;
  revision?: number;
  line_item_code?: string | null;
  line_item_description?: string | null;
  scope: string;
  scope_type: QuoteScopeType;
  status: QuoteStatus;
  amount: number;
  is_qualified: boolean;
  qualification_notes: string[];
  is_selected: boolean;
  selection_reason?: string | null;
  exclusions: string[];
  notes?: string | null;
};

export type QuoteComparisonLine = {
  line_item_code?: string | null;
  line_item_description: string;
  scope: string;
  scope_type: QuoteScopeType;
  lowest_supplier?: string | null;
  lowest_amount?: number | null;
  selected_supplier?: string | null;
  selected_amount?: number | null;
  selected_is_lowest: boolean;
  selection_reason?: string | null;
  quote_count: number;
  qualified_quote_count: number;
  ready_for_estimate: boolean;
  blockers: string[];
};

export type QuoteComparisonResponse = {
  lines: QuoteComparisonLine[];
  total_lowest: number;
  total_selected: number;
  delta_from_lowest: number;
  ready_for_estimate: boolean;
  blockers: string[];
};

export type QuoteSelectionDecision = {
  line_item_code?: string | null;
  line_item_description: string;
  scope: string;
  scope_type: QuoteScopeType;
  lowest_qualified_supplier?: string | null;
  lowest_qualified_amount?: number | null;
  selected_supplier?: string | null;
  selected_amount?: number | null;
  selected_is_lowest: boolean;
  selection_reason?: string | null;
  quote_count: number;
  qualified_quote_count: number;
  ready_for_estimate: boolean;
  blockers: string[];
};

export type QuoteEstimateSelectionResponse = {
  decisions: QuoteSelectionDecision[];
  line_items: EstimateLineItem[];
  ready_for_estimate: boolean;
  blockers: string[];
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

  if (!response.ok) {
    throw new Error(`Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const quotesApi = {
  compare: (quotes: SupplierQuoteCreate[]) =>
    request<QuoteComparisonResponse>("/quotes/compare", {
      method: "POST",
      body: JSON.stringify({ quotes }),
    }),
  estimateSelection: (quotes: SupplierQuoteCreate[]) =>
    request<QuoteEstimateSelectionResponse>("/quotes/estimate-selection", {
      method: "POST",
      body: JSON.stringify({ quotes }),
    }),
};
