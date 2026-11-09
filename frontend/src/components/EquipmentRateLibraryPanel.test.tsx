import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { equipmentRatesApi } from "../api/equipmentRates";
import { EquipmentRateLibraryPanel } from "./EquipmentRateLibraryPanel";

vi.mock("../api/equipmentRates", () => ({
  equipmentRatesApi: {
    library: vi.fn(),
    calculate: vi.fn(),
    exportDraft: vi.fn(),
  },
}));

describe("EquipmentRateLibraryPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(equipmentRatesApi.library).mockResolvedValue({
      regional_markets: ["vancouver_metro_west", "surrey_fraser_valley_east"],
      benchmarks: [{
        rate_category: "equipment",
        equipment_class: "Excavator",
        equipment_description: "20-23 t",
        base_rate: 228,
        operator_included: true,
        source_name: "IEOA 2026 Suggested Equipment Rates",
        source_url: "https://www.ieoa.ca/rates/",
        source_effective_date: "2026-01-01",
        price_on_request: false,
      }],
      default_target_margin_percent: 10,
      currency: "CAD",
      gst_included: false,
    });
  });

  it("converts a vendor period and displays the controlled selected rate", async () => {
    const user = userEvent.setup();
    vi.mocked(equipmentRatesApi.calculate).mockResolvedValue({
      hourly_base_rate: 100,
      hourly_rental_direct_cost: 100,
      hourly_all_in_direct_cost: 150,
      calculated_client_rate: 166.67,
      selected_client_rate: 228,
      minimum_billable_amount: 912,
      standby_rate: 0,
      operator_labour_to_add: 0,
      approval_required: false,
      approval_reasons: [],
      approval_status: "draft",
      source_name: "Vendor quote",
      audit_components: {},
    });

    render(<EquipmentRateLibraryPanel />);
    await user.selectOptions(await screen.findByLabelText("Equipment class"), "0");
    await user.type(screen.getByLabelText("Vendor base rental"), "800");
    await user.type(screen.getByLabelText("Operator hourly direct cost"), "50");
    await user.type(screen.getByLabelText("Vendor/source name"), "Vendor quote");
    await user.click(screen.getByRole("button", { name: "Calculate controlled rate" }));

    expect(equipmentRatesApi.calculate).toHaveBeenCalledWith(expect.objectContaining({
      base_rate: 800,
      included_hours: 8,
      operator_hourly_cost: 50,
      market_benchmark_rate: 228,
      target_margin_percent: 10,
    }));
    expect(await screen.findByText("$228.00/hr")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /export draft pdf/i })).toBeEnabled();
  });
});
