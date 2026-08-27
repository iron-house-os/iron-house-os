import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CompletedWorkCostLedger, financeApi } from "../api/finance";
import { CompletedWorkCostPanel } from "./CompletedWorkCostPanel";


vi.mock("../api/finance", () => ({
  financeApi: {
    getCompletedWorkCosts: vi.fn(),
    createCompletedWorkCost: vi.fn(),
  },
}));

const ledger: CompletedWorkCostLedger = {
  project_id: "project-359",
  project_name: "Verified Project",
  source_line_count: 1,
  linked_line_count: 0,
  unlinked_line_count: 1,
  linked_actual_cost_total: 0,
  warning: "Billable quantities, rates, and amounts are revenue evidence only. Linked entries are explicit internal actual costs; this view does not prove that every project cost is captured or that project margin is complete.",
  lines: [{
    id: "11111111-1111-4111-8111-111111111111",
    work_date: "2026-08-11",
    source_import_key: "bowline-rawlison-2026-08-25",
    source_line_key: "01-common-excavation-2026-08-11",
    source_invoice_number: "BOW-2026-0811",
    source_drive_file_id: "drive-source-1",
    description: "Common excavation",
    quantity: "12.5",
    unit: "hour",
    billable_rate: "220.00",
    billable_amount: "2750.00",
    internal_cost_status: "internal_cost_unverified",
    linked_actual_cost_total: 0,
    linked_entries: [],
  }],
};

const created = {
  created: true,
  idempotent: false,
  entry: {
    id: "22222222-2222-4222-8222-222222222222",
    project_id: "project-359",
    cost_code: "02-100",
    entry_type: "actual",
    category: "equipment",
    amount: 612.5,
    entry_date: "2026-08-11",
    vendor_name: null,
    vendor_address: null,
    reference: "EQUIPMENT-LOG-0811",
    description: "Verified excavator internal cost",
    status: "posted",
    source_type: "completed_work_actual",
    source_id: ledger.lines[0].id,
    source_key: "33333333-3333-4333-8333-333333333333",
  },
};


describe("CompletedWorkCostPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(financeApi.getCompletedWorkCosts).mockResolvedValue(ledger);
    vi.mocked(financeApi.createCompletedWorkCost).mockResolvedValue(created);
  });

  it("keeps revenue evidence display-only and submits only explicit internal cost input", async () => {
    const user = userEvent.setup();
    render(<CompletedWorkCostPanel projectId="project-359" />);

    const panel = await screen.findByRole("region", { name: "Completed-work actual costs" });
    expect(panel).toHaveTextContent("revenue evidence only");
    expect(panel).toHaveTextContent("$2,750.00");
    expect(screen.getByLabelText("Actual cost (CAD)")).toHaveValue(null);

    await user.type(screen.getByLabelText("Cost code"), "02-100");
    await user.selectOptions(screen.getByLabelText("Cost category"), "equipment");
    await user.type(screen.getByLabelText("Actual cost (CAD)"), "612.50");
    await user.type(screen.getByLabelText("Cost entry date"), "2026-08-11");
    await user.type(screen.getByLabelText("Evidence description"), "Verified excavator internal cost");
    await user.type(screen.getByLabelText("Reference (if known)"), "EQUIPMENT-LOG-0811");
    await user.click(screen.getByRole("button", { name: "Record explicit actual cost" }));

    await waitFor(() => expect(financeApi.createCompletedWorkCost).toHaveBeenCalledTimes(1));
    const payload = vi.mocked(financeApi.createCompletedWorkCost).mock.calls[0][1];
    expect(payload).toMatchObject({
      completed_work_id: ledger.lines[0].id,
      cost_code: "02-100",
      category: "equipment",
      amount: 612.5,
      entry_date: "2026-08-11",
      reference: "EQUIPMENT-LOG-0811",
      description: "Verified excavator internal cost",
    });
    expect(payload.idempotency_key).toEqual(expect.stringMatching(/^[0-9a-f-]{36}$/));
    expect(payload).not.toHaveProperty("billable_rate");
    expect(payload).not.toHaveProperty("billable_amount");
    expect(await screen.findByRole("status")).toHaveTextContent("Verified internal actual cost recorded");
  });

  it("reuses the request key for an unchanged retry after an ambiguous failure", async () => {
    vi.mocked(financeApi.createCompletedWorkCost)
      .mockRejectedValueOnce(new Error("Connection interrupted"))
      .mockResolvedValueOnce({ ...created, created: false, idempotent: true });
    const user = userEvent.setup();
    render(<CompletedWorkCostPanel projectId="project-359" />);
    await screen.findByText("Common excavation");

    await user.type(screen.getByLabelText("Cost code"), "02-100");
    await user.selectOptions(screen.getByLabelText("Cost category"), "equipment");
    await user.type(screen.getByLabelText("Actual cost (CAD)"), "612.50");
    await user.type(screen.getByLabelText("Cost entry date"), "2026-08-11");
    await user.type(screen.getByLabelText("Evidence description"), "Verified excavator internal cost");
    await user.click(screen.getByRole("button", { name: "Record explicit actual cost" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Connection interrupted");
    await user.click(screen.getByRole("button", { name: "Record explicit actual cost" }));

    await waitFor(() => expect(financeApi.createCompletedWorkCost).toHaveBeenCalledTimes(2));
    const firstKey = vi.mocked(financeApi.createCompletedWorkCost).mock.calls[0][1].idempotency_key;
    const secondKey = vi.mocked(financeApi.createCompletedWorkCost).mock.calls[1][1].idempotency_key;
    expect(secondKey).toBe(firstKey);
    expect(await screen.findByRole("status")).toHaveTextContent("Exact retry confirmed");
  });
});
