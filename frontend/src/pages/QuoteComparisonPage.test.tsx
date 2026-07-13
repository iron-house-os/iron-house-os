import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { QuoteComparisonPage } from "./QuoteComparisonPage";

const requestBodies: Record<string, unknown>[] = [];

const comparisonResponse = {
  lines: [
    {
      line_item_code: "PIPE-001",
      line_item_description: "PVC storm pipe supply",
      scope: "Supply PVC storm pipe",
      scope_type: "material",
      lowest_supplier: "Lowest Supplier",
      lowest_amount: 10000,
      selected_supplier: "Preferred Supplier",
      selected_amount: 11250,
      selected_is_lowest: false,
      selection_reason: "Complete scope and confirmed delivery",
      quote_count: 2,
      qualified_quote_count: 2,
      ready_for_estimate: true,
      blockers: [],
    },
  ],
  total_lowest: 10000,
  total_selected: 11250,
  delta_from_lowest: 1250,
  ready_for_estimate: true,
  blockers: [],
};

const selectionResponse = {
  decisions: [
    {
      line_item_code: "PIPE-001",
      line_item_description: "PVC storm pipe supply",
      scope: "Supply PVC storm pipe",
      scope_type: "material",
      lowest_qualified_supplier: "Lowest Supplier",
      lowest_qualified_amount: 10000,
      selected_supplier: "Preferred Supplier",
      selected_amount: 11250,
      selected_is_lowest: false,
      selection_reason: "Complete scope and confirmed delivery",
      quote_count: 2,
      qualified_quote_count: 2,
      ready_for_estimate: true,
      blockers: [],
    },
  ],
  line_items: [
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
  ready_for_estimate: true,
  blockers: [],
};

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function EstimateHandoffProbe() {
  const location = useLocation();
  const state = location.state as typeof selectionResponse | { quoteLineItems: typeof selectionResponse.line_items };
  const lineItems = "quoteLineItems" in state ? state.quoteLineItems : [];
  return <div>{location.pathname}: {lineItems[0]?.vendor_quotes[0]?.supplier}</div>;
}

describe("QuoteComparisonPage", () => {
  beforeEach(() => {
    requestBodies.length = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        requestBodies.push(JSON.parse(String(init?.body)));
        const url = String(input);
        if (url.endsWith("/quotes/compare")) return jsonResponse(comparisonResponse);
        if (url.endsWith("/quotes/estimate-selection")) return jsonResponse(selectionResponse);
        throw new Error(`Unexpected request: ${url}`);
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("qualifies a documented non-low supplier and hands it to Estimating", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/quotes?projectId=WR26-012&projectName=Marine%20Drive"]}>
        <Routes>
          <Route path="/quotes" element={<QuoteComparisonPage />} />
          <Route path="/estimating" element={<EstimateHandoffProbe />} />
        </Routes>
      </MemoryRouter>,
    );

    const suppliers = screen.getAllByLabelText("Supplier");
    const codes = screen.getAllByLabelText("Line Item Code");
    const descriptions = screen.getAllByLabelText("Line Item");
    const scopes = screen.getAllByLabelText("Scope");
    const amounts = screen.getAllByLabelText("Amount");
    const reasons = screen.getAllByLabelText("Selection Reason");

    await user.type(suppliers[0], "Lowest Supplier");
    await user.type(suppliers[1], "Preferred Supplier");
    await user.type(codes[0], "PIPE-001");
    await user.type(codes[1], "PIPE-001");
    await user.type(descriptions[0], "PVC storm pipe supply");
    await user.type(descriptions[1], "PVC storm pipe supply");
    await user.type(scopes[0], "Supply PVC storm pipe");
    await user.type(scopes[1], "Supply PVC storm pipe");
    await user.clear(amounts[0]);
    await user.type(amounts[0], "10000");
    await user.clear(amounts[1]);
    await user.type(amounts[1], "11250");
    await user.click(screen.getAllByLabelText("Selected quote")[1]);
    await user.type(reasons[1], "Complete scope and confirmed delivery");

    await user.click(screen.getByRole("button", { name: "Compare and qualify quotes" }));

    expect(await screen.findByText("Ready for estimate: every line has one qualified supplier selection.")).toBeInTheDocument();
    expect(screen.getByText("Not lowest")).toBeInTheDocument();
    expect(screen.getByText("Complete scope and confirmed delivery")).toBeInTheDocument();

    await waitFor(() => expect(requestBodies).toHaveLength(2));
    expect(requestBodies[0]).toEqual(
      expect.objectContaining({
        quotes: expect.arrayContaining([
          expect.objectContaining({
            supplier_name: "Preferred Supplier",
            is_qualified: true,
            is_selected: true,
            selection_reason: "Complete scope and confirmed delivery",
          }),
        ]),
      }),
    );

    await user.click(screen.getByRole("button", { name: "Use selected quotes in estimate" }));
    expect(await screen.findByText("/estimating: Preferred Supplier")).toBeInTheDocument();
  });
});
