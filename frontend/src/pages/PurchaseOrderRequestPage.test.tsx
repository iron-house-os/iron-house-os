import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fieldOperationsApi } from "../api/fieldOperations";
import { PurchaseOrderRequestPage } from "./PurchaseOrderRequestPage";

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "admin-1", email: "admin@ironhousecontracting.com", role: "admin" },
    portalRole: "management",
  }),
}));

vi.mock("../api/fieldOperations", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/fieldOperations")>();
  return {
    ...actual,
    fieldOperationsApi: {
      ...actual.fieldOperationsApi,
      bootstrap: vi.fn(),
      createRecord: vi.fn(),
    },
  };
});

describe("PurchaseOrderRequestPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    window.history.replaceState({}, "", "/request-po?projectId=job-1&projectName=Linked+Job");
    vi.mocked(fieldOperationsApi.bootstrap).mockResolvedValue({
      projects: [
        { id: "job-1", name: "Linked Job", project_number: "IH-2026-030" },
        { id: "job-2", name: "Second Job", project_number: "IH-2026-031" },
      ],
      suppliers: [],
      cost_codes: [],
      records: [],
    } as never);
  });

  afterEach(() => vi.unstubAllGlobals());

  it("preselects the job carried from the guided workflow", async () => {
    renderPo("/request-po?projectId=job-1&projectName=Linked+Job");

    expect(await screen.findByRole("combobox", { name: "Job" })).toHaveValue("job-1");
    expect(screen.getByRole("option", { name: "IH-2026-030 Linked Job" })).toBeInTheDocument();
  });

  it("updates the selected job when workflow context changes without unmounting", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/request-po?projectId=job-1&projectName=Linked+Job"]}>
        <PoRouteHarness />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("combobox", { name: "Job" })).toHaveValue("job-1");
    await user.click(screen.getByRole("button", { name: "Open second job" }));

    await waitFor(() => expect(screen.getByRole("combobox", { name: "Job" })).toHaveValue("job-2"));
  });

  it("keeps an explicit workflow draft authoritative over routed project context", async () => {
    window.history.replaceState({}, "", "/request-po?draftId=draft-1&projectId=job-1&projectName=Linked+Job");
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      id: "draft-1",
      owner_account_id: "admin-1",
      project_id: "job-2",
      workflow_type: "purchase_order_request",
      title: "PO request — Aggregate",
      payload: { projectId: "job-2", supplierId: "", costCode: "", purpose: "Aggregate", amount: "" },
      schema_version: 1,
      revision: 2,
      status: "active",
      last_saved_at: "2026-08-21T12:00:00Z",
      created_at: "2026-08-21T11:00:00Z",
      updated_at: "2026-08-21T12:00:00Z",
    }), { status: 200, headers: { "Content-Type": "application/json" } })));

    renderPo("/request-po?draftId=draft-1&projectId=job-1&projectName=Linked+Job");

    const jobSelect = await screen.findByRole("combobox", { name: "Job" });
    await waitFor(() => expect(jobSelect).toHaveValue("job-2"));
    expect(screen.getByPlaceholderText(/20 m of 200 mm PVC/)).toHaveValue("Aggregate");
  });

  it("generates a PO with one separator and a hyphen-free job code", async () => {
    vi.spyOn(Date, "now").mockReturnValue(12345678);
    vi.mocked(fieldOperationsApi.createRecord).mockResolvedValue({} as never);
    const user = userEvent.setup();
    renderPo("/request-po?projectId=job-1&projectName=Linked+Job");

    await screen.findByRole("combobox", { name: "Job" });
    await user.type(screen.getByPlaceholderText(/20 m of 200 mm PVC/), "Pipe and fittings");
    await user.click(screen.getByRole("button", { name: "Request PO" }));

    await waitFor(() => expect(fieldOperationsApi.createRecord).toHaveBeenCalledWith(expect.objectContaining({
      title: "PO12345678-IH2026030 — Pipe and fittings",
      details: expect.objectContaining({
        po_number: "PO12345678-IH2026030",
        job_number: "IH-2026-030",
      }),
    })));
    const createdPo = vi.mocked(fieldOperationsApi.createRecord).mock.calls[0]?.[0] as { details?: Record<string, unknown> } | undefined;
    const poNumber = String(createdPo?.details?.po_number ?? "");
    expect(poNumber.match(/-/g)).toHaveLength(1);
    expect(poNumber.split("-")[1]).toMatch(/^IH\d{7}$/);
    expect(await screen.findByText("Created PO12345678-IH2026030 and sent for approval.")).toBeInTheDocument();
  });
});

function renderPo(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><PurchaseOrderRequestPage /></MemoryRouter>);
}

function PoRouteHarness() {
  const navigate = useNavigate();
  return <>
    <button type="button" onClick={() => navigate("/request-po?projectId=job-2&projectName=Second+Job")}>Open second job</button>
    <PurchaseOrderRequestPage />
  </>;
}
