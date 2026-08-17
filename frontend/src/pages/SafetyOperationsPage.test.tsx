import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fieldOperationsApi } from "../api/fieldOperations";
import { SafetyOperationsPage } from "./SafetyOperationsPage";

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { role: "operations_manager" } }),
}));

vi.mock("../api/fieldOperations", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/fieldOperations")>();
  return {
    ...actual,
    fieldOperationsApi: {
      ...actual.fieldOperationsApi,
      bootstrap: vi.fn(),
      createRecord: vi.fn(),
      updateSafetyStatus: vi.fn(),
    },
  };
});

describe("SafetyOperationsPage", () => {
  beforeEach(() => {
    vi.mocked(fieldOperationsApi.bootstrap).mockResolvedValue({
      employees: [{ id: "worker-1", first_name: "Crew", last_name: "Member", email: "crew@example.com" }],
      records: [{
        id: "incident-1",
        record_type: "incident",
        project_id: null,
        employee_id: "worker-1",
        equipment_id: null,
        supplier_id: null,
        cost_code: null,
        work_date: "2026-08-17",
        title: "Excavator swing near miss",
        status: "reported",
        severity: "high",
        details: {
          occurrence_kind: "near_miss",
          location: "Field Operations Test",
          description: "A worker entered the boundary.",
          immediate_controls: "Work stopped and the boundary was reset.",
        },
        document_ids: [],
        signatures: [],
        alert_recipients: ["Jeremie Peters", "Mac Warren"],
        submitted_by: "manager@example.com",
      }],
    } as never);
  });

  it("shows durable incident review and management-only first-aid workflows", async () => {
    const user = userEvent.setup();
    render(<SafetyOperationsPage />);

    expect(await screen.findByText("Open incidents")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Incidents / near misses" }));
    expect(screen.getByText("Excavator swing near miss")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start review" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "First-aid occurrences" }));
    expect(screen.getByText(/Minimum necessary operational record/)).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Crew Member" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save confidential record" })).toBeInTheDocument();
  });
});
