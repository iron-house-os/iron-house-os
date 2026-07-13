import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EstimatingPage } from "./EstimatingPage";

const summaryPayloads: Record<string, unknown>[] = [];

const rateLibrary = {
  production_rates: [
    {
      activity: "excavation",
      description: "Bulk excavation and loading",
      unit: "m3",
      production_rate_per_hour: 30,
      crew: [],
      equipment: [],
      notes: "Normal access",
    },
  ],
};

const estimateSummary = {
  project_name: "Marine Drive Parking Lot",
  project_code: "WR26-012",
  direct_cost: 10000,
  indirect_cost: 1000,
  risk_cost: 500,
  subtotal_before_markup: 11500,
  contingency: 575,
  bonding: 0,
  insurance: 0,
  overhead: 603.75,
  profit: 1267.88,
  final_price: 13946.63,
  gross_margin_percent: 28.3,
  category_breakdown: {
    labour: 2500,
    equipment: 3000,
    material: 1500,
    disposal: 500,
    subcontract: 2500,
    indirect: 1000,
    risk: 500,
  },
  line_items: [
    {
      code: "31-001",
      description: "Excavation",
      item_type: "self_perform",
      quantity: 25,
      unit: "m3",
      hours: 0.83,
      labour_cost: 2500,
      equipment_cost: 3000,
      material_cost: 0,
      disposal_cost: 500,
      subcontract_cost: 4000,
      direct_cost: 10000,
      unit_cost: 400,
      selected_quote_supplier: "Qualified Hauling",
      selected_quote_amount: 4000,
    },
  ],
  assumptions: ["Normal working hours"],
  exclusions: ["Contaminated soil disposal"],
};

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("EstimatingPage", () => {
  beforeEach(() => {
    summaryPayloads.length = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/estimates/rate-library")) return jsonResponse(rateLibrary);
        if (url.endsWith("/estimates/summary")) {
          summaryPayloads.push(JSON.parse(String(init?.body)));
          return jsonResponse(estimateSummary);
        }
        throw new Error(`Unexpected request: ${url}`);
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("submits production, disposal, quote, risk, and markup inputs and renders the summary", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <EstimatingPage />
      </MemoryRouter>,
    );

    await screen.findByRole("option", { name: "Excavation — 30/hr" });

    const quantity = screen.getByLabelText("Line item 1 quantity");
    await user.clear(quantity);
    await user.type(quantity, "25");
    await user.selectOptions(screen.getByLabelText("Line item 1 production activity"), "excavation");

    await user.type(screen.getByLabelText("Line item 1 quote supplier"), "Qualified Hauling");
    await user.clear(screen.getByLabelText("Line item 1 quoted scope"));
    await user.type(screen.getByLabelText("Line item 1 quoted scope"), "Haul excavated material");
    await user.clear(screen.getByLabelText("Line item 1 quote amount"));
    await user.type(screen.getByLabelText("Line item 1 quote amount"), "4000");
    await user.type(screen.getByLabelText("Line item 1 quote notes"), "Complete scope");

    await user.type(screen.getByLabelText("Line item 1 disposal material"), "Native soil");
    await user.clear(screen.getByLabelText("Line item 1 disposal quantity"));
    await user.type(screen.getByLabelText("Line item 1 disposal quantity"), "20");
    await user.clear(screen.getByLabelText("Line item 1 disposal unit cost"));
    await user.type(screen.getByLabelText("Line item 1 disposal unit cost"), "18");
    await user.clear(screen.getByLabelText("Line item 1 disposal haul cost"));
    await user.type(screen.getByLabelText("Line item 1 disposal haul cost"), "7");
    await user.type(screen.getByLabelText("Line item 1 disposal facility"), "Valley Transfer");

    await user.click(screen.getByRole("button", { name: /Calculate/i }));

    expect(await screen.findByText("$13,947")).toBeInTheDocument();
    expect(screen.getByText("Selected supplier: Qualified Hauling")).toBeInTheDocument();

    await waitFor(() => expect(summaryPayloads).toHaveLength(1));
    const submitted = summaryPayloads[0];
    expect(submitted.line_items).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          quantity: 25,
          default_activity: "excavation",
          disposal: [
            expect.objectContaining({
              material: "Native soil",
              quantity: 20,
              unit_cost: 18,
              haul_cost: 7,
              facility: "Valley Transfer",
            }),
          ],
          vendor_quotes: [
            expect.objectContaining({
              supplier: "Qualified Hauling",
              amount: 4000,
              notes: "Complete scope",
            }),
          ],
        }),
      ]),
    );
    expect(submitted.markup).toEqual(
      expect.objectContaining({
        contingency_percent: 10,
        overhead_percent: 5,
        profit_percent: 10,
      }),
    );
    expect(submitted.risks).toEqual([
      expect.objectContaining({ amount: 500, probability: 1 }),
    ]);
  });

  it("blocks calculation and workbook export until a project name is entered", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <EstimatingPage />
      </MemoryRouter>,
    );

    await screen.findByRole("option", { name: "Excavation — 30/hr" });
    fireEvent.change(screen.getByLabelText("Project name"), { target: { value: "" } });

    await user.click(screen.getByRole("button", { name: /Calculate/i }));
    expect(
      await screen.findByText("Project name is required before calculating or exporting an estimate."),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Workbook/i }));

    const fetchMock = vi.mocked(fetch);
    expect(
      fetchMock.mock.calls.some(([input]) => String(input).endsWith("/estimates/summary")),
    ).toBe(false);
    expect(
      fetchMock.mock.calls.some(([input]) => String(input).endsWith("/estimates/workbook")),
    ).toBe(false);
  });
});
