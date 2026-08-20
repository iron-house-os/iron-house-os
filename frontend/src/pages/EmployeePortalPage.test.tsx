import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { FieldOperationsBootstrap, fieldOperationsApi } from "../api/fieldOperations";
import { EmployeePortalPage, incidentWorkDate } from "./EmployeePortalPage";

vi.mock("../api/fieldOperations", () => ({
  fieldOperationsApi: { bootstrap: vi.fn() },
}));
vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { email: "employee@ironhousecontracting.com", role: "viewer" } }),
}));

const bootstrap = {
  employees: [], projects: [], suppliers: [], equipment: [], cost_codes: [],
  job_workbooks: [], production_items: [], material_types: [], material_movement_summary: [],
  milestone_catalog: [], milestone_recognitions: [], paperwork_recognitions: [], vehicles: [],
  vehicle_logs: [], time_entries: [], records: [], certifications: [], alerts: [], flha_presets: [],
  toolbox_talk: { week_of: "2026-08-20", title: "Test", summary: "Test", discussion_points: [], source_name: "WorkSafeBC", source_url: "https://www.worksafebc.com" },
  operator_access: { authorized: false, employee_id: "employee-1", blockers: ["No current operational equipment or vehicle assignment is recorded."], assignments: [], orientation_status: "Ready", qualification_record_id: null },
} as unknown as FieldOperationsBootstrap;

describe("EmployeePortalPage", () => {
  beforeEach(() => {
    vi.mocked(fieldOperationsApi.bootstrap).mockResolvedValue(bootstrap);
  });

  it("presents separate linked workspaces instead of one long employee page", () => {
    render(<MemoryRouter><EmployeePortalPage /></MemoryRouter>);

    expect(screen.getByRole("heading", { name: "Employee Portal" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /my time/i })).toHaveAttribute("href", "/employee-portal/time");
    expect(screen.getByRole("link", { name: /safety and toolbox talks/i })).toHaveAttribute("href", "/employee-portal/safety");
    expect(screen.getByRole("link", { name: /small equipment inspections/i })).toHaveAttribute("href", "/employee-portal/small-equipment");
    expect(screen.getByRole("link", { name: /operator tools/i })).toHaveAttribute("href", "/employee-portal/operator");
  });

  it("shows operator tools as blocked when assignment and qualification gates are not ready", async () => {
    render(<MemoryRouter><EmployeePortalPage section="operator" /></MemoryRouter>);

    expect(await screen.findByText("Operator actions blocked")).toBeInTheDocument();
    expect(screen.getByText("No current operational equipment or vehicle assignment is recorded.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /operator time/i })).not.toBeInTheDocument();
  });

  it("keeps operator qualification requests available outside the gated operator actions", async () => {
    render(<MemoryRouter><EmployeePortalPage section="milestones" /></MemoryRouter>);

    expect(await screen.findByText("Career milestones and recognition")).toBeInTheDocument();
    expect(screen.getByText("Operator qualification milestones")).toBeInTheDocument();
  });

  it("opens assigned operator workflows inside Employee Portal after server authorization", async () => {
    vi.mocked(fieldOperationsApi.bootstrap).mockResolvedValue({
      ...bootstrap,
      operator_access: {
        authorized: true,
        employee_id: "employee-1",
        blockers: [],
        assignments: [{ resource_type: "equipment", resource_id: "equipment-1", name: "EX-01 Excavator", status: "available" }],
        orientation_status: "Ready",
        qualification_record_id: "qualification-1",
      },
    });
    render(<MemoryRouter><EmployeePortalPage section="operator" /></MemoryRouter>);

    expect(await screen.findByText("Authorised for assigned resources")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /operator time/i })).toHaveAttribute("href", "/employee-portal/operator/time");
    expect(screen.getByRole("link", { name: /assigned machine inspections/i })).toHaveAttribute("href", "/employee-portal/operator/inspections");
  });

  it("derives an incident work date from the captured occurrence time", () => {
    expect(incidentWorkDate("2026-08-11T06:45", "2026-08-18")).toBe("2026-08-11");
    expect(incidentWorkDate("", "2026-08-18")).toBe("2026-08-18");
    expect(incidentWorkDate("2026-02-30T06:45", "2026-08-18")).toBe("2026-08-18");
  });
});
