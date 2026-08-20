import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  employeeOnboardingApi,
  OnboardingRecord,
  requiredOnboardingItems,
} from "../api/employeeOnboarding";
import { EmployeeOnboardingPortalPage } from "./EmployeeOnboardingPortalPage";

vi.mock("../api/employeeOnboarding", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/employeeOnboarding")>();
  return {
    ...original,
    employeeOnboardingApi: {
      portalRecord: vi.fn(),
      savePortalProgress: vi.fn(),
      submitPortal: vi.fn(),
    },
  };
});

const invitationRecord: OnboardingRecord = {
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
  status: "in_progress",
  completion_percent: 0,
  missing_items: requiredOnboardingItems.map(([code]) => code),
  reviewer_id: null,
  correction_note: null,
  invitation_expires_at: "2026-08-23T08:00:00Z",
  invited_at: "2026-08-20T08:00:00Z",
  submitted_at: null,
  approved_at: null,
  activated_at: null,
  created_at: "2026-08-20T08:00:00Z",
  updated_at: "2026-08-20T08:00:00Z",
};

describe("EmployeeOnboardingPortalPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(employeeOnboardingApi.portalRecord).mockResolvedValue(invitationRecord);
    vi.mocked(employeeOnboardingApi.savePortalProgress).mockResolvedValue(invitationRecord);
    vi.mocked(employeeOnboardingApi.submitPortal).mockResolvedValue({
      ...invitationRecord,
      status: "submitted",
      completion_percent: 100,
      missing_items: [],
      submitted_at: "2026-08-20T12:00:00Z",
    });
  });

  it("submits only after every required item and acknowledgement are checked", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/employee-onboarding/secure-token"]}>
        <Routes>
          <Route path="/employee-onboarding/:token" element={<EmployeeOnboardingPortalPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await screen.findByRole("heading", { name: "Welcome, Alex" });
    const submit = screen.getByRole("button", { name: "Submit for review" });
    expect(submit).toBeDisabled();

    for (const [, label] of requiredOnboardingItems) {
      await user.click(screen.getByRole("checkbox", { name: label }));
    }
    await user.click(screen.getByRole("checkbox", { name: /I confirm the checked items/i }));
    expect(submit).toBeEnabled();
    await user.click(submit);

    await waitFor(() => expect(employeeOnboardingApi.submitPortal).toHaveBeenCalledWith(
      "secure-token",
      requiredOnboardingItems.map(([code]) => code),
      true,
    ));
    expect(await screen.findByText("Submitted for review")).toBeInTheDocument();
  });
});
