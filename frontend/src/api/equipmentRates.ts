import { apiFetch } from "./client";

export type RegionalMarket = "vancouver_metro_west" | "surrey_fraser_valley_east";
export type RateCategory =
  | "labour"
  | "equipment"
  | "attachment"
  | "support_vehicle_light_equipment"
  | "trucking_disposal"
  | "mobilization_logistics";
export type RentalPeriod = "hour" | "day" | "week" | "month";

export type EquipmentBenchmark = {
  rate_category: RateCategory;
  equipment_class: string;
  equipment_description: string;
  base_rate: number | null;
  operator_included: boolean;
  source_name: string;
  source_url: string;
  source_effective_date: string;
  price_on_request: boolean;
};

export type EquipmentRateLibrary = {
  regional_markets: RegionalMarket[];
  benchmarks: EquipmentBenchmark[];
  default_target_margin_percent: number;
  currency: string;
  gst_included: boolean;
};

export type EquipmentRateInput = {
  regional_market: RegionalMarket;
  rate_category: RateCategory;
  equipment_class: string;
  equipment_description: string;
  ownership_basis: "rented" | "owned" | "subcontracted";
  rate_basis: "industry_benchmark" | "vendor_quote" | "owned_cost_model" | "contract_rate";
  operator_included: boolean;
  base_rate: number;
  rental_period: RentalPeriod;
  included_hours: number;
  overtime_hour_rate?: number;
  fuel_included?: boolean;
  fuel_cost?: number;
  fuel_surcharge_percent?: number;
  damage_waiver_percent_or_amount?: number;
  damage_waiver_is_percent?: boolean;
  rental_fees?: number;
  attachment_rate?: number;
  delivery_cost?: number;
  pickup_cost?: number;
  cleanup_allowance?: number;
  operator_hourly_cost?: number;
  project_support_hourly_cost?: number;
  mobilization_rate?: number;
  minimum_billable_hours?: number;
  standby_rate?: number;
  target_margin_percent: number;
  market_benchmark_rate?: number | null;
  contract_rate?: number | null;
  source_name: string;
  source_url?: string;
  source_effective_date?: string | null;
  quote_expiry_date?: string | null;
  override_reason?: string | null;
  approval_status?: "draft" | "pending" | "approved" | "rejected";
  waive_mobilization?: boolean;
  waive_minimum?: boolean;
  operator_inclusion_changed?: boolean;
};

export type EquipmentRateResult = {
  hourly_base_rate: number;
  hourly_rental_direct_cost: number;
  hourly_all_in_direct_cost: number;
  calculated_client_rate: number;
  selected_client_rate: number;
  minimum_billable_amount: number;
  standby_rate: number;
  operator_labour_to_add: number;
  approval_required: boolean;
  approval_reasons: string[];
  approval_status: string;
  source_name: string;
  audit_components: Record<string, number>;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await apiFetch(`${API_BASE_URL}${path}`, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const equipmentRatesApi = {
  library: () => request<EquipmentRateLibrary>("/estimates/equipment-rate-library"),
  calculate: (payload: EquipmentRateInput) => request<EquipmentRateResult>(
    "/estimates/equipment-rate",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  ),
  exportDraft: async (payload: EquipmentRateInput) => {
    const effective = new Date();
    const expiry = new Date(effective);
    expiry.setDate(expiry.getDate() + 30);
    const response = await apiFetch(`${API_BASE_URL}/estimates/client-rate-sheet`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "Iron House Client Rate Sheet",
        effective_date: effective.toISOString().slice(0, 10),
        expiry_date: expiry.toISOString().slice(0, 10),
        regional_market: payload.regional_market,
        lines: [payload],
      }),
    });
    if (!response.ok) throw new Error("Unable to export draft rate sheet");
    return response.blob();
  },
};
