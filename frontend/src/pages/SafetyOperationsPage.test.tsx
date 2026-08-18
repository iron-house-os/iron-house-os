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
      safetyAnalytics: vi.fn(),
      createRecord: vi.fn(),
      updateSafetyStatus: vi.fn(),
    },
  };
});

describe("SafetyOperationsPage", () => {
  beforeEach(() => {
    vi.mocked(fieldOperationsApi.safetyAnalytics).mockResolvedValue({
      as_of: "2026-08-18",
      safety_controls_total: 12,
      blocked_permits: 2,
      at_risk_permits: 1,
      open_corrective_actions: 3,
      overdue_corrective_actions: 1,
      active_emergency_cards: 2,
      flha_last_30_days: 8,
      toolbox_talks_last_30_days: 4,
      open_incidents: 1,
      credentials_expiring_60_days: 2,
      credentials_expired: 1,
      audit_export_records: 12,
      confidential_record_types_excluded: ["first_aid_record", "incident"],
    });
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
      }, {
        id: "emergency-1",
        record_type: "emergency_action_card",
        project_id: null,
        employee_id: null,
        equipment_id: null,
        supplier_id: null,
        cost_code: null,
        work_date: "2026-08-17",
        title: "River Road emergency card",
        status: "ready",
        severity: "medium",
        details: {
          project: "River Road",
          address: "100 River Road",
          muster: "North gate",
          firstAid: "Site office",
          emergencyLead: "Site supervisor",
          rescue: "Stop work and report to muster point",
        },
        document_ids: [],
        signatures: [],
        alert_recipients: [],
        submitted_by: "manager@example.com",
      }],
    } as never);
  });

  it("shows durable incident review and management-only first-aid workflows", async () => {
    const user = userEvent.setup();
    render(<SafetyOperationsPage />);

    expect(await screen.findByText("Open incidents")).toBeInTheDocument();
    expect(screen.getByText("Management safety analytics")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Export audit CSV" })).toHaveAttribute("href", expect.stringContaining("/field-operations/safety/audit.csv"));
    expect(screen.getByText(/Incident and first-aid occurrence records/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Emergency cards" }));
    expect(screen.getByRole("link", { name: "PDF / save offline" })).toHaveAttribute("href", expect.stringContaining("/emergency-action-card.pdf"));
    await user.click(screen.getByText("Show QR field link"));
    expect(await screen.findByRole("img", { name: "QR field link for River Road" })).toBeInTheDocument();
    expect(screen.getByText(/no password or access token/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Incidents / near misses" }));
    expect(screen.getByText("Excavator swing near miss")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start review" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "First-aid occurrences" }));
    expect(screen.getByText(/Minimum necessary operational record/)).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Crew Member" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save confidential record" })).toBeInTheDocument();
  });
});
