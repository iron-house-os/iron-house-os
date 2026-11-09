import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { dailyTimesheetApi } from "../api/dailyTimesheets";
import { DailyTimesheetWorkflow } from "./DailyTimesheetWorkflow";

vi.mock("../api/dailyTimesheets", async () => {
  const actual = await vi.importActual<typeof import("../api/dailyTimesheets")>("../api/dailyTimesheets");
  return { ...actual, dailyTimesheetApi: { bootstrap: vi.fn(), save: vi.fn(), submit: vi.fn(), action: vi.fn(), revision: vi.fn(), post: vi.fn(), pdfUrl: vi.fn((id) => `/pdf/${id}`), csvUrl: vi.fn() } };
});
vi.mock("../api/media", () => ({ mediaApi: { upload: vi.fn(), list: vi.fn().mockResolvedValue([]) } }));
vi.mock("../contexts/AuthContext", () => ({ useAuth: () => ({ user: { id: "user-115", email: "foreman115@example.com" } }) }));

const bootstrap = {
  projects: [{ id: "job-1", name: "Main Street", project_number: "IH-115", status: "active" }],
  employees: [{ id: "foreman-1", code: "EMP-F", name: "Fran Foreman", classification: "Foreman", portal_role: "foreman" }, { id: "worker-1", code: "EMP-W", name: "Casey Crew", classification: "Pipe Layer", portal_role: "employee" }],
  equipment: [{ id: "eq-1", name: "Excavator", identifier: "EX-1", status: "available" }],
  rentals: [], vendors: [{ id: "vendor-1", name: "Aggregate Supply", category: "materials" }], receipts: [{ id: "receipt-1", reference: "R-115", vendor_name: "Aggregate Supply", receipt_date: "2026-08-02", status: "approved" }],
  project_cost_codes: { "job-1": [{ code: "03-100", name: "Excavation" }, { code: "31-200", name: "Pipe installation" }] }, assigned_crew: { "job-1": ["worker-1"] }, sheets: [], can_approve: false,
};

describe("DailyTimesheetWorkflow", () => {
  beforeEach(() => { localStorage.clear(); vi.clearAllMocks(); vi.mocked(dailyTimesheetApi.bootstrap).mockResolvedValue(bootstrap); vi.mocked(dailyTimesheetApi.save).mockResolvedValue({ id: "sheet-1", status: "draft", version: 1, project_id: "job-1", work_date: "2026-08-02", shift: "day", details: {}, document_ids: [], ticket_document_ids: [], submitted_by: null, created_at: "", updated_at: "" }); });

  it("loads assigned crew, filters estimate cost codes, and calculates ST/OT running totals", async () => {
    render(<DailyTimesheetWorkflow />);
    const job = await screen.findByLabelText("Job number and name");
    fireEvent.change(job, { target: { value: "job-1" } });
    fireEvent.change(screen.getByLabelText("Foreman / supervisor"), { target: { value: "foreman-1" } });
    expect(await screen.findByText(/EMP-W · Casey Crew/)).toBeInTheDocument();
    const costCode = screen.getByLabelText("Job cost code");
    expect(within(costCode).getAllByRole("option").map((item) => item.textContent)).toEqual(["Select…", "03-100 — Excavation", "31-200 — Pipe installation"]);
    fireEvent.change(costCode, { target: { value: "03-100" } });
    fireEvent.change(screen.getByLabelText("ST"), { target: { value: "8" } });
    fireEvent.change(screen.getByLabelText("OT"), { target: { value: "1.5" } });
    expect(screen.getByText(/ST 8.00 · OT 1.50 · 9.50 hours/)).toBeInTheDocument();
    await waitFor(() => expect(dailyTimesheetApi.save).toHaveBeenCalled(), { timeout: 2500 });
    expect(localStorage.getItem("ihos:foreman-daily-timesheet:v1:user-115")).toContain('"project_id":"job-1"');
    expect(localStorage.getItem("ihos:foreman-daily-timesheet:v1")).toBeNull();
  });

  it("adds equipment and a mixed material/production line with receipt linkage", async () => {
    render(<DailyTimesheetWorkflow />); await screen.findByText("Foreman Daily Time Sheet");
    fireEvent.change(screen.getByLabelText("Job number and name"), { target: { value: "job-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Owned" }));
    expect(screen.getByLabelText("Fleet unit")).toHaveValue("eq-1");
    fireEvent.click(screen.getByRole("button", { name: "Add line" }));
    fireEvent.change(screen.getByLabelText("Material / fee description"), { target: { value: "Pipe bedding" } });
    fireEvent.change(screen.getByLabelText("Supplier / vendor"), { target: { value: "vendor-1" } });
    fireEvent.change(screen.getByLabelText("Existing receipt record"), { target: { value: "receipt-1" } });
    expect(screen.getByLabelText("Existing receipt record")).toHaveValue("receipt-1");
    expect(screen.getByText(/Mixed lines may use separate job cost codes/)).toBeInTheDocument();
  });

  it("keeps field photos and ticket photos as separate multi-image collections", async () => {
    render(<DailyTimesheetWorkflow />);
    await screen.findByText("Foreman Daily Time Sheet");

    expect(screen.getByText("Field production photos")).toBeInTheDocument();
    expect(screen.getByText("Delivery / disposal ticket photos")).toBeInTheDocument();
  });

  it("restores totals after refresh and updates the existing server draft", async () => {
    const first = render(<DailyTimesheetWorkflow />);
    fireEvent.change(await screen.findByLabelText("Job number and name"), { target: { value: "job-1" } });
    fireEvent.change(screen.getByLabelText("Foreman / supervisor"), { target: { value: "foreman-1" } });
    fireEvent.change(screen.getByLabelText("Job cost code"), { target: { value: "03-100" } });
    fireEvent.change(screen.getByLabelText("ST"), { target: { value: "8" } });
    fireEvent.change(screen.getByLabelText("OT"), { target: { value: "1.5" } });
    await waitFor(() => expect(dailyTimesheetApi.save).toHaveBeenCalled(), { timeout: 2500 });
    await waitFor(() => expect(localStorage.getItem("ihos:foreman-daily-timesheet:v1:user-115")).toContain('"sheetId":"sheet-1"'));

    first.unmount();
    vi.mocked(dailyTimesheetApi.save).mockClear();
    render(<DailyTimesheetWorkflow />);

    expect(await screen.findByText(/ST 8.00 · OT 1.50 · 9.50 hours/)).toBeInTheDocument();
    await waitFor(() => expect(dailyTimesheetApi.save).toHaveBeenCalledWith(expect.any(Object), "sheet-1"), { timeout: 2500 });
  });
});
