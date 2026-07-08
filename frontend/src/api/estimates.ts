export type EstimateUnit = "LS" | "EA" | "m" | "m2" | "m3" | "t" | "hr" | "day";

export type EstimateItemType = "self_perform" | "material" | "subcontract" | "indirect" | "allowance";

export type DefaultProductionActivity =
  | "pipe_installation"
  | "excavation"
  | "bedding"
  | "backfill"
  | "asphalt_removal"
  | "concrete_removal"
  | "manhole_installation"
  | "catch_basin_installation"
  | "sidewalk"
  | "curb"
  | "traffic_control"
  | "landscaping";

export type LabourCrewMember = {
  role: string;
  quantity: number;
  hourly_rate: number;
  burden_percent: number;
};

export type EquipmentResource = {
  name: string;
  quantity: number;
  hourly_rate: number;
  daily_rate?: number | null;
  owned_or_rented?: string | null;
};

export type MaterialInput = {
  name: string;
  quantity: number;
  unit: EstimateUnit;
  unit_cost: number;
  supplier?: string | null;
  waste_percent: number;
};

export type VendorQuoteInput = {
  supplier: string;
  scope: string;
  amount: number;
  is_selected: boolean;
  notes?: string | null;
};

export type EstimateLineItem = {
  code?: string | null;
  description: string;
  item_type: EstimateItemType;
  quantity: number;
  unit: EstimateUnit;
  production_rate_per_hour?: number | null;
  default_activity?: DefaultProductionActivity | null;
  labour: LabourCrewMember[];
  equipment: EquipmentResource[];
  materials: MaterialInput[];
  vendor_quotes: VendorQuoteInput[];
  direct_unit_cost?: number | null;
  notes?: string | null;
};

export type EstimateIndirect = {
  description: string;
  amount: number;
  category?: string | null;
};

export type EstimateRiskAllowance = {
  description: string;
  amount: number;
  probability?: number | null;
  notes?: string | null;
};

export type EstimateMarkup = {
  overhead_percent: number;
  profit_percent: number;
  contingency_percent: number;
  bonding_percent: number;
  insurance_percent: number;
};

export type EstimateCreate = {
  project_name: string;
  project_code?: string | null;
  owner?: string | null;
  estimator?: string | null;
  line_items: EstimateLineItem[];
  indirects: EstimateIndirect[];
  risks: EstimateRiskAllowance[];
  markup: EstimateMarkup;
  assumptions: string[];
  exclusions: string[];
};

export type TakeoffHandoffItem = {
  code?: string | null;
  description: string;
  category: string;
  quantity: number;
  unit: EstimateUnit;
  source?: string | null;
  confidence: number;
  drawing_reference?: string | null;
  notes?: string | null;
};

export type EstimateHandoffRequest = {
  project_name: string;
  project_code?: string | null;
  items: TakeoffHandoffItem[];
};

export type EstimateHandoffResponse = {
  project_name: string;
  project_code?: string | null;
  line_items: EstimateLineItem[];
  warnings: string[];
  assumptions: string[];
};

export type EstimateLineItemCost = {
  code?: string | null;
  description: string;
  item_type: EstimateItemType;
  quantity: number;
  unit: EstimateUnit;
  hours: number;
  labour_cost: number;
  equipment_cost: number;
  material_cost: number;
  disposal_cost: number;
  subcontract_cost: number;
  direct_cost: number;
  unit_cost: number;
  selected_quote_supplier?: string | null;
  selected_quote_amount?: string | null;
};

export type EstimateCategoryBreakdown = {
  labour: number;
  equipment: number;
  material: number;
  disposal: number;
  subcontract: number;
  indirect: number;
  risk: number;
};

export type EstimateSummary = {
  project_name: string;
  project_code?: string | null;
  direct_cost: number;
  indirect_cost: number;
  risk_cost: number;
  subtotal_before_markup: number;
  contingency: number;
  bonding: number;
  insurance: number;
  overhead: number;
  profit: number;
  final_price: number;
  gross_margin_percent: number;
  category_breakdown: EstimateCategoryBreakdown;
  line_items: EstimateLineItemCost[];
  assumptions: string[];
  exclusions: string[];
};

export type ProductionRate = {
  activity: DefaultProductionActivity;
  description: string;
  unit: EstimateUnit;
  production_rate_per_hour: number;
  crew: LabourCrewMember[];
  equipment: EquipmentResource[];
  notes?: string | null;
};

export type RateLibrary = {
  production_rates: ProductionRate[];
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

export const estimatesApi = {
  rateLibrary: () => request<RateLibrary>("/estimates/rate-library"),
  handoff: (payload: EstimateHandoffRequest) =>
    request<EstimateHandoffResponse>("/estimates/handoff", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  summary: (payload: EstimateCreate) =>
    request<EstimateSummary>("/estimates/summary", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  workbookUrl: () => `${API_BASE_URL}/estimates/workbook`,
};