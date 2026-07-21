import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EstimatingPage } from "./EstimatingPage";

const summaryPayloads: Record<string, unknown>[] = [];

const testProject = {
  id: "11111111-1111-4111-8111-111111111111",
  name: "Test Project",
  project_number: "TEST-001",
  status: "tendering",
  updated_at: "2026-07-21T12:00:00Z",
};

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
        if (url.endsWith("/projects")) return jsonResponse({ items: [testProject], total: 1 });
        if (url.endsWith(`/estimates/workspace/project/${testProject.id}`)) {
          return jsonResponse({ items: [], total: 0 });
        }
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
      expect.objectContaining({ amount: 0, probability: 1 }),
    ]);
  });

  it("loads qualified supplier selections from quote comparison state", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter
        initialEntries={[
          {
            pathname: "/estimating",
            state: {
              quoteLineItems: [
                {
                  code: "PIPE-001",
                  description: "PVC storm pipe supply",
                  item_type: "material",
                  quantity: 1,
                  unit: "LS",
                  labour: [],
                  equipment: [],
                  materials: [],
                  disposal: [],
                  vendor_quotes: [
                    {
                      supplier: "Preferred Supplier",
                      scope: "Supply PVC storm pipe",
                      amount: 11250,
                      is_qualified: true,
                      qualification_notes: [],
                      is_selected: true,
                      selection_reason: "Complete scope and confirmed delivery",
                      notes: "Confirmed delivery",
                    },
                    {
                      supplier: "Lowest Supplier",
                      scope: "Supply PVC storm pipe",
                      amount: 10000,
                      is_qualified: true,
                      qualification_notes: [],
                      is_selected: false,
                      selection_reason: null,
                      notes: null,
                    },
                  ],
                  direct_unit_cost: null,
                  notes: "Supplier selection: Complete scope and confirmed delivery",
                },
              ],
            },
          },
        ]}
      >
        <EstimatingPage />
      </MemoryRouter>,
    );

    expect(
      await screen.findByText("Loaded 1 estimate line item from qualified supplier selections."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Line item 1 quote supplier")).toHaveValue("Preferred Supplier");
    expect(screen.getByLabelText("Line item 1 quote amount")).toHaveValue(11250);
    expect(screen.getByLabelText("Line item 1 selection reason")).toHaveValue(
      "Complete scope and confirmed delivery",
    );
    expect(screen.getByText("1 qualified alternative quote retained for workbook comparison.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Calculate/i }));

    await waitFor(() => expect(summaryPayloads).toHaveLength(1));
    const submitted = summaryPayloads[0] as {
      line_items: Array<{ vendor_quotes: unknown[] }>;
    };
    expect(submitted.line_items[0].vendor_quotes).toEqual([
      expect.objectContaining({
        supplier: "Preferred Supplier",
        is_selected: true,
        selection_reason: "Complete scope and confirmed delivery",
      }),
      expect.objectContaining({
        supplier: "Lowest Supplier",
        is_selected: false,
      }),
    ]);
  });

  it("loads the selected project's latest saved estimate instead of the Marine Drive sample", async () => {
    const tfnProject = {
      ...testProject,
      id: "22222222-2222-4222-8222-222222222222",
      name: "TFN Path",
      project_number: "TFN-2026-003",
    };
    const savedEstimate = {
      project_name: "TFN Path",
      project_code: "TFN-2026-003",
      line_items: [
        {
          code: "32-1216",
          description: "Hot mix asphalt paving",
          item_type: "subcontract",
          quantity: 3235,
          unit: "m2",
          default_activity: null,
          labour: [],
          equipment: [],
          materials: [],
          disposal: [],
          vendor_quotes: [],
          direct_unit_cost: 75,
        },
      ],
      indirects: [{ description: "Mobilization", amount: 75000, category: "mobilization" }],
      risks: [{ description: "Schedule escalation", amount: 100000, probability: 0.5 }],
      markup: {
        contingency_percent: 3,
        overhead_percent: 10,
        profit_percent: 12.5,
        bonding_percent: 1.5,
        insurance_percent: 1,
      },
      assumptions: ["Firm pricing through May 2027"],
      exclusions: ["Unidentified hazardous materials"],
    };

    vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/projects")) return jsonResponse({ items: [tfnProject], total: 1 });
      if (url.endsWith(`/estimates/workspace/project/${tfnProject.id}`)) {
        return jsonResponse({
          items: [
            {
              id: "33333333-3333-4333-8333-333333333333",
              project_id: tfnProject.id,
              status: "draft",
              estimate: { source: "tfn_bid_loader_v1", estimate: savedEstimate, summary: null },
              created_at: "2026-07-21T12:00:00Z",
              updated_at: "2026-07-21T12:00:00Z",
            },
          ],
          total: 1,
        });
      }
      if (url.endsWith("/estimates/rate-library")) return jsonResponse(rateLibrary);
      throw new Error(`Unexpected request: ${url}`);
    });

    render(
      <MemoryRouter initialEntries={[`/estimating?projectId=${tfnProject.id}&projectName=TFN%20Path`]}>
        <EstimatingPage />
      </MemoryRouter>,
    );

    expect(await screen.findByDisplayValue("TFN Path")).toBeInTheDocument();
    expect(screen.getByDisplayValue("TFN-2026-003")).toBeInTheDocument();
    expect(screen.getByLabelText("Line item 1 description")).toHaveValue("Hot mix asphalt paving");
    expect(screen.getByLabelText("Line item 1 quantity")).toHaveValue(3235);
    expect(screen.getByLabelText("Profit %")).toHaveValue(12.5);
    expect(screen.queryByDisplayValue("Marine Drive Parking Lot")).not.toBeInTheDocument();
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
