import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { employeeOnboardingApi, OnboardingRecord } from "../api/employeeOnboarding";
import { fieldOperationsApi } from "../api/fieldOperations";
import { EmployeeOnboardingPage } from "./EmployeeOnboardingPage";

vi.mock("../api/employeeOnboarding", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/employeeOnboarding")>();
  return {
    ...original,
    employeeOnboardingApi: {
      list: vi.fn(),
      positions: vi.fn(),
      create: vi.fn(),
      invite: vi.fn(),
      reviewPacket: vi.fn(),
      revoke: vi.fn(),
      requestCorrections: vi.fn(),
      approve: vi.fn(),
      activate: vi.fn(),
      deploymentStatus: vi.fn(),
    },
  };
});

vi.mock("../api/fieldOperations", () => ({
  fieldOperationsApi: { bootstrap: vi.fn() },
}));

const record: OnboardingRecord = {
  id: "onboarding-1",
  legal_first_name: "Alex",
  legal_last_name: "Operator",
  preferred_name: "Alex",
  personal_email: "alex.operator@example.com",
  mobile_phone: null,
  category: "field_staff",
  position: "equipment_operator",
  supervisor_id: null,
  employment_type: "full_time",
  start_date: "2026-08-20",
  primary_location: "Yard",
  onboarding_package: "standard-field",
  status: "approved",
  completion_percent: 100,
  missing_items: [],
  reviewer_id: "admin-1",
  correction_note: null,
  invitation_expires_at: null,
  invited_at: null,
  submitted_at: "2026-08-20T10:00:00Z",
  approved_at: "2026-08-20T11:00:00Z",
  activated_at: null,
  created_at: "2026-08-20T08:00:00Z",
  updated_at: "2026-08-20T11:00:00Z",
};

describe("EmployeeOnboardingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(employeeOnboardingApi.list).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(employeeOnboardingApi.positions).mockResolvedValue([
      { value: "green_labourer", label: "Green Labourer", category: "field_staff", level: 1 },
      { value: "equipment_operator", label: "Equipment Operator", category: "field_staff", level: 7 },
      { value: "admin", label: "Admin", category: "office_staff", level: 1 },
    ]);
    vi.mocked(fieldOperationsApi.bootstrap).mockResolvedValue({ employees: [] } as never);
    vi.mocked(employeeOnboardingApi.create).mockResolvedValue(record);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("creates a new hire from controlled onboarding fields", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><EmployeeOnboardingPage /></MemoryRouter>);

    await screen.findByRole("option", { name: "Equipment Operator" });
    await user.type(screen.getByRole("textbox", { name: "Legal first name" }), "Taylor");
    await user.type(screen.getByRole("textbox", { name: "Legal last name" }), "Operator");
    await user.type(screen.getByRole("textbox", { name: "Personal email" }), "taylor@example.com");
    await user.selectOptions(screen.getByRole("combobox", { name: "Position" }), "equipment_operator");
    await user.click(screen.getByRole("button", { name: "Create onboarding record" }));

    await waitFor(() => expect(employeeOnboardingApi.create).toHaveBeenCalledTimes(1));
    expect(employeeOnboardingApi.create).toHaveBeenCalledWith(expect.objectContaining({
      legal_first_name: "Taylor",
      legal_last_name: "Operator",
      personal_email: "taylor@example.com",
      category: "field_staff",
      position: "equipment_operator",
      onboarding_package: "standard-field",
    }));
  });

  it("shows one-time credentials only after ready approved activation", async () => {
    const user = userEvent.setup();
    vi.mocked(employeeOnboardingApi.list).mockResolvedValue({ items: [record], total: 1 });
    vi.mocked(employeeOnboardingApi.deploymentStatus).mockResolvedValue({
      status: "Ready",
      blockers: [],
      latest_company_orientation_id: "orientation-1",
      latest_site_orientation_id: "orientation-2",
    });
    vi.mocked(employeeOnboardingApi.activate).mockResolvedValue({
      onboarding: { ...record, status: "active", activated_at: "2026-08-20T12:00:00Z" },
      employee_id: "employee-1",
      account_id: "account-1",
      username: "alex.operator@example.com",
      temporary_password: "one-time-password-2026",
      portal_role: "operator",
    });
    render(<MemoryRouter><EmployeeOnboardingPage /></MemoryRouter>);

    await user.click(await screen.findByRole("button", { name: "Activate and create login" }));

    expect(await screen.findByText("one-time-password-2026")).toBeInTheDocument();
    expect(screen.getByText("alex.operator@example.com")).toBeInTheDocument();
    expect(screen.getByText("operator portal")).toBeInTheDocument();
    expect(employeeOnboardingApi.activate).toHaveBeenCalledWith("onboarding-1");
  });

  it("generates a local downloadable QR for the exact current employee invitation", async () => {
    const user = userEvent.setup();
    const draft = { ...record, status: "draft" as const, completion_percent: 0, missing_items: ["personal_information"] };
    vi.mocked(employeeOnboardingApi.list).mockResolvedValue({ items: [draft], total: 1 });
    vi.mocked(employeeOnboardingApi.deploymentStatus).mockResolvedValue({ status: "Blocked", blockers: ["Company orientation has not been recorded."], latest_company_orientation_id: null, latest_site_orientation_id: null });
    vi.mocked(employeeOnboardingApi.invite).mockResolvedValue({ onboarding_id: draft.id, invite_url: "https://staging.os.ironhousecivil.com/employee-onboarding/current-token", expires_at: "2026-08-23T10:00:00Z" });
    render(<MemoryRouter><EmployeeOnboardingPage /></MemoryRouter>);

    await user.click(await screen.findByRole("button", { name: "Generate invitation" }));

    expect(await screen.findByRole("img", { name: "Onboarding QR code for Alex" })).toHaveAttribute("src", expect.stringMatching(/^data:image\/svg\+xml/));
    expect(screen.getByRole("link", { name: "Download QR" })).toHaveAttribute("download", "ihos-onboarding-alex.svg");
    expect(screen.getByRole("button", { name: "Email or share QR" })).toBeInTheDocument();
    expect(employeeOnboardingApi.invite).toHaveBeenCalledWith("onboarding-1");
  });

  it("handles an iPad share-sheet cancellation without an unhandled rejection", async () => {
    const user = userEvent.setup();
    const draft = { ...record, status: "draft" as const, completion_percent: 0, missing_items: ["personal_information"] };
    const share = vi.fn().mockRejectedValue(new DOMException("Share cancelled", "AbortError"));
    vi.stubGlobal("navigator", { share, canShare: () => true });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      blob: async () => new Blob(["<svg />"], { type: "image/svg+xml" }),
    }));
    vi.mocked(employeeOnboardingApi.list).mockResolvedValue({ items: [draft], total: 1 });
    vi.mocked(employeeOnboardingApi.deploymentStatus).mockResolvedValue({ status: "Blocked", blockers: ["Company orientation has not been recorded."], latest_company_orientation_id: null, latest_site_orientation_id: null });
    vi.mocked(employeeOnboardingApi.invite).mockResolvedValue({ onboarding_id: draft.id, invite_url: "https://staging.os.ironhousecivil.com/employee-onboarding/current-token", expires_at: "2026-08-23T10:00:00Z" });
    render(<MemoryRouter><EmployeeOnboardingPage /></MemoryRouter>);

    await user.click(await screen.findByRole("button", { name: "Generate invitation" }));
    await screen.findByRole("img", { name: "Onboarding QR code for Alex" });
    await user.click(screen.getByRole("button", { name: "Email or share QR" }));

    expect(await screen.findByText("Sharing cancelled. The current invitation and QR remain available.")).toBeInTheDocument();
    expect(share).toHaveBeenCalledTimes(1);
  });

  it("falls back to an email link when the device cannot share the QR", async () => {
    const user = userEvent.setup();
    const draft = { ...record, status: "draft" as const, completion_percent: 0, missing_items: ["personal_information"] };
    const share = vi.fn().mockRejectedValue(new Error("Share unavailable"));
    vi.stubGlobal("navigator", { share, canShare: () => true });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      blob: async () => new Blob(["<svg />"], { type: "image/svg+xml" }),
    }));
    vi.mocked(employeeOnboardingApi.list).mockResolvedValue({ items: [draft], total: 1 });
    vi.mocked(employeeOnboardingApi.deploymentStatus).mockResolvedValue({ status: "Blocked", blockers: ["Company orientation has not been recorded."], latest_company_orientation_id: null, latest_site_orientation_id: null });
    vi.mocked(employeeOnboardingApi.invite).mockResolvedValue({ onboarding_id: draft.id, invite_url: "https://staging.os.ironhousecivil.com/employee-onboarding/current-token", expires_at: "2026-08-23T10:00:00Z" });
    render(<MemoryRouter><EmployeeOnboardingPage /></MemoryRouter>);

    await user.click(await screen.findByRole("button", { name: "Generate invitation" }));
    await screen.findByRole("img", { name: "Onboarding QR code for Alex" });
    await user.click(screen.getByRole("button", { name: "Email or share QR" }));

    expect(await screen.findByText("The device could not attach the QR. Opening an email with the secure link instead.")).toBeInTheDocument();
    expect(share).toHaveBeenCalledTimes(1);
  });
});
