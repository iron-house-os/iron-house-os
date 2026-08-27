import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EstimateCreate, EstimateSummary } from "../api/estimates";
import { EstimateWorkspacePanel } from "./EstimateWorkspacePanel";

const estimate: EstimateCreate = {
  project_name: "Bennett Road concrete repair",
  project_code: null,
  line_items: [{
    code: "CON-001",
    description: "Concrete pull and pour",
    item_type: "self_perform",
    quantity: 1,
    unit: "LS",
    default_activity: null,
    labour: [],
    equipment: [],
    materials: [],
    disposal: [],
    vendor_quotes: [],
    direct_unit_cost: 10000,
  }],
  indirects: [],
  risks: [],
  markup: {
    contingency_percent: 0,
    overhead_percent: 0,
    profit_percent: 20,
    bonding_percent: 0,
    insurance_percent: 0,
  },
  assumptions: ["Normal weekday access"],
  exclusions: ["Hazardous material removal"],
  base_hourly_wage: 0,
  labour_chargeout_multiplier: 2.1,
  target_margin_percent: 10,
  planned_field_shifts: null,
};

const summary: EstimateSummary = {
  project_name: estimate.project_name,
  project_code: null,
  direct_cost: 10000,
  indirect_cost: 0,
  risk_cost: 0,
  subtotal_before_markup: 10000,
  contingency: 0,
  bonding: 0,
  insurance: 0,
  overhead: 0,
  profit: 2000,
  final_price: 12000,
  gross_margin_percent: 16.67,
  category_breakdown: {
    labour: 0,
    equipment: 0,
    material: 0,
    disposal: 0,
    subcontract: 0,
    indirect: 0,
    risk: 0,
  },
  line_items: [{
    code: "CON-001",
    description: "Concrete pull and pour",
    item_type: "self_perform",
    quantity: 1,
    unit: "LS",
    hours: 0,
    labour_cost: 0,
    equipment_cost: 0,
    material_cost: 0,
    disposal_cost: 0,
    subcontract_cost: 0,
    direct_cost: 10000,
    unit_cost: 10000,
  }],
  assumptions: estimate.assumptions,
  exclusions: estimate.exclusions,
  base_hourly_wage: 0,
  labour_chargeout_multiplier: 2.1,
  target_margin_percent: 10,
  planned_field_shifts: null,
  small_job_tier: "more_than_5_shifts",
  small_job_premium_percent: 0,
  calculated_labour_chargeout_rate: 0,
  labour_chargeout_total: 0,
  override_reason: null,
};

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("EstimateWorkspacePanel", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("saves the calculated estimate and opens its generated quote draft", async () => {
    const requests: Array<{ url: string; init?: RequestInit }> = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      requests.push({ url, init });
      if (url.endsWith("/estimates/workspace")) {
        return jsonResponse({
          id: "workspace-1",
          project_id: "project-1",
          status: "draft",
          estimate: { source: "estimate_workspace", estimate, summary },
          created_at: "2026-08-27T00:00:00Z",
          updated_at: "2026-08-27T00:00:00Z",
        }, 201);
      }
      if (url.endsWith("/customer-quotes/from-estimate/workspace-1")) {
        return jsonResponse({ id: "quote-1" }, 201);
      }
      throw new Error(`Unexpected request: ${url}`);
    }));

    render(
      <MemoryRouter initialEntries={["/estimating"]}>
        <Routes>
          <Route path="/estimating" element={<EstimateWorkspacePanel projectId="project-1" estimate={estimate} summary={summary} />} />
          <Route path="/customer-quotes" element={<div>Quote draft destination</div>} />
        </Routes>
      </MemoryRouter>,
    );

    await userEvent.setup().click(screen.getByRole("button", { name: "Create quote draft" }));

    expect(await screen.findByText("Quote draft destination")).toBeInTheDocument();
    expect(requests.map((request) => request.url)).toEqual([
      expect.stringMatching(/\/estimates\/workspace$/),
      expect.stringMatching(/\/customer-quotes\/from-estimate\/workspace-1$/),
    ]);
    expect(JSON.parse(String(requests[0].init?.body))).toEqual({
      project_id: "project-1",
      status: "draft",
      estimate,
      summary,
    });
  });

  it("keeps quote creation unavailable until the estimate is calculated", async () => {
    render(
      <MemoryRouter>
        <EstimateWorkspacePanel projectId="project-1" estimate={estimate} summary={null} />
      </MemoryRouter>,
    );

    expect(screen.getByRole("button", { name: "Create quote draft" })).toBeDisabled();
  });
});
