import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FieldOperationsBootstrap } from "../api/fieldOperations";
import { FLHAWorkflow } from "./FLHAWorkflow";

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { email: "foreperson@example.com", role: "viewer" } }),
}));

const employee = {
  id: "10000000-0000-0000-0000-000000000001", first_name: "Field", last_name: "Foreperson",
  email: "foreperson@example.com", role: "Foreperson", phone: null, address: null,
  emergency_contact_name: null, emergency_contact_phone: null, emergency_contact_relationship: null,
  hire_date: null, portal_role: "foreman" as const, notes: null, status: "active",
};

const data = {
  employees: [employee],
  projects: [{ id: "20000000-0000-0000-0000-000000000001", name: "River Road" }],
  records: [],
  flha_presets: [
    { id: "company-excavation", scope: "company", name: "Excavation and utility work", rows: [{ task: "Excavate", hazard: "Utility contact", control: "Verify current locates", control_level: "engineering", risk: "critical", evidence_required: true }] },
    { id: "project-setup", scope: "project", project_id: "20000000-0000-0000-0000-000000000001", name: "River Road site setup", rows: [] },
  ],
} as unknown as FieldOperationsBootstrap;

describe("FLHAWorkflow", () => {
  it("presents the complete mobile-first field card and critical-hazard block state", () => {
    render(<FLHAWorkflow data={data} canCreate onSaved={vi.fn()} onError={vi.fn()} />);

    expect(screen.getByRole("heading", { name: "Daily FLHA" })).toBeInTheDocument();
    expect(screen.getByText("Underground utilities and current locates")).toBeInTheDocument();
    expect(screen.getByText("Excavation sloping / shoring and safe access")).toBeInTheDocument();
    expect(screen.getByText("Emergency response and stop-work")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Custom row" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add River Road site setup" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Add Excavation and utility work" }));
    expect(screen.getByText(/Blocked: 1 critical hazard/)).toBeInTheDocument();
    expect(screen.getByText(/never mark an FLHA safe or complete/i)).toBeInTheDocument();
  });
});
