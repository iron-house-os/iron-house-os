import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fieldOperationsApi } from "../api/fieldOperations";
import { FLHAPage } from "./FLHAPage";

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({
    user: {
      id: "00000000-0000-0000-0000-000000000001",
      email: "foreman@ironhousecontracting.com",
      display_name: "Field Foreman",
      role: "operations_manager",
    },
    portalRole: "management",
  }),
}));

vi.mock("../components/UniversalPhotoField", () => ({
  UniversalPhotoField: () => <div>Shared authorized photo viewer</div>,
}));

vi.mock("../api/fieldOperations", async () => {
  const actual = await vi.importActual<typeof import("../api/fieldOperations")>("../api/fieldOperations");
  return {
    ...actual,
    fieldOperationsApi: {
      ...actual.fieldOperationsApi,
      bootstrap: vi.fn(),
      createFlha: vi.fn(),
      updateFlha: vi.fn(),
      releaseFlha: vi.fn(),
      signFlha: vi.fn(),
      reassessFlha: vi.fn(),
      suggestFlha: vi.fn(),
    },
  };
});

describe("FLHAPage", () => {
  beforeEach(() => {
    vi.mocked(fieldOperationsApi.bootstrap).mockResolvedValue({
      employees: [{
        id: "00000000-0000-0000-0000-000000000002",
        first_name: "Field",
        last_name: "Foreman",
        email: "foreman@ironhousecontracting.com",
        role: "Foreperson",
        phone: null,
        address: null,
        emergency_contact_name: null,
        emergency_contact_phone: null,
        emergency_contact_relationship: null,
        hire_date: null,
        portal_role: "management",
        notes: null,
        status: "active",
      }],
      projects: [{ id: "00000000-0000-0000-0000-000000000003", name: "Mobile FLHA Project" }],
      suppliers: [],
      equipment: [],
      cost_codes: [],
      job_workbooks: [],
      production_items: [],
      material_types: [],
      material_movement_summary: [],
      milestone_catalog: [],
      milestone_recognitions: [],
      paperwork_recognitions: [],
      vehicles: [],
      vehicle_logs: [],
      time_entries: [],
      records: [],
      certifications: [],
      alerts: [],
      toolbox_talk: {
        week_of: "2026-08-03",
        title: "Safety",
        summary: "Safety",
        discussion_points: [],
        source_name: "IHOS",
        source_url: "https://example.com",
      },
    });
  });

  it("renders a mobile-first guarded workflow with all required screening controls", async () => {
    render(<MemoryRouter><FLHAPage /></MemoryRouter>);

    expect(screen.getByRole("heading", { name: "Field Level Hazard Assessment" })).toBeInTheDocument();
    expect(screen.getByText(/AI remains advisory/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "2. Fast hazard screening" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "yes" })).toHaveLength(10);
    expect(screen.getAllByRole("button", { name: "no" })).toHaveLength(10);
    expect(screen.getAllByRole("button", { name: "N/A" })).toHaveLength(10);
    expect(screen.getByRole("button", { name: /suggest hazard\/control/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /verify field conditions and release/i })).not.toBeInTheDocument();

    await waitFor(() => expect(screen.getByLabelText("Project / job")).toHaveValue("00000000-0000-0000-0000-000000000003"));
    expect(screen.getByLabelText(/Field Foreman/)).toBeChecked();
  });
});

