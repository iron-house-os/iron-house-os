import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { employeeOnboardingApi, OnboardingRecord, PortalPacket } from "../api/employeeOnboarding";
import { EmployeeOnboardingPortalPage } from "./EmployeeOnboardingPortalPage";

vi.mock("../api/employeeOnboarding", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/employeeOnboarding")>();
  return { ...original, employeeOnboardingApi: { portalRecord: vi.fn(), savePortalProgress: vi.fn(), submitPortal: vi.fn() } };
});

const invitationRecord: OnboardingRecord = {
  id: "onboarding-1", legal_first_name: "Alex", legal_last_name: "Operator", preferred_name: "Alex",
  personal_email: "alex.operator@example.com", mobile_phone: null, category: "field_staff",
  position: "equipment_operator", supervisor_id: null, employment_type: "full_time",
  start_date: "2026-08-20", primary_location: "Yard", onboarding_package: "standard-field",
  status: "in_progress", completion_percent: 0, missing_items: [], reviewer_id: null,
  correction_note: null, invitation_expires_at: "2026-08-23T08:00:00Z", invited_at: "2026-08-20T08:00:00Z",
  submitted_at: null, approved_at: null, activated_at: null, created_at: "2026-08-20T08:00:00Z", updated_at: "2026-08-20T08:00:00Z",
};

const emptyPacket: PortalPacket = {
  personal_information: null, address: null, emergency_contact: null, payroll: null, tax_forms: null,
  employment_agreements: null, certifications: null, ppe_requirements: null, signature_name: null, signed_at: null,
};

const completePacket: PortalPacket = {
  personal_information: { preferred_name: "Alex", mobile_phone: "250-555-0114", date_of_birth: "1990-01-02" },
  address: { street_address: "100 Main Street", unit: null, city: "Dawson Creek", province: "BC", postal_code: "V1G 1A1", country: "Canada" },
  emergency_contact: { full_name: "Jordan Operator", relationship: "Partner", primary_phone: "250-555-0188", alternate_phone: null },
  payroll: { payment_method: "cheque", account_holder_name: null, institution_number: null, transit_number: null, account_number: null, direct_deposit_authorized: false },
  tax_forms: { form_year: 2026, social_insurance_number: "046454286", country_of_permanent_residence: "Canada", federal_claim_amounts: ["16452", ...Array(11).fill("0")], bc_claim_amounts: ["13216", ...Array(9).fill("0")], federal_more_than_one_employer: false, federal_total_income_less_than_claim: false, non_resident_world_income_90_percent_or_more: null, additional_tax_per_payment: "0", bc_more_than_one_employer: false, bc_total_income_less_than_claim: false, federal_certified: true, bc_certified: true },
  employment_agreements: { employment_terms_reviewed: true, company_policies_reviewed: true, privacy_notice_reviewed: true, purchase_receipt_standard_reviewed: true, questions_resolved: true },
  certifications: { none_to_report: true, certifications: [] },
  ppe_requirements: { site_ppe_required: true, boot_size: "10", glove_size: "L", shirt_size: "L", trouser_size: "34x32", prescription_safety_glasses: false, respirator_fit_test_required: false, notes: null },
  signature_name: null, signed_at: null,
};

function renderPortal() {
  render(<MemoryRouter initialEntries={["/employee-onboarding/secure-token"]}><Routes><Route path="/employee-onboarding/:token" element={<EmployeeOnboardingPortalPage />} /></Routes></MemoryRouter>);
}

describe("EmployeeOnboardingPortalPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(employeeOnboardingApi.portalRecord).mockResolvedValue({ onboarding: invitationRecord, packet: emptyPacket });
    vi.mocked(employeeOnboardingApi.savePortalProgress).mockImplementation(async (_token, packet) => ({ onboarding: invitationRecord, packet }));
    vi.mocked(employeeOnboardingApi.submitPortal).mockResolvedValue({ onboarding: { ...invitationRecord, status: "submitted", completion_percent: 100, submitted_at: "2026-08-20T12:00:00Z" }, packet: { ...completePacket, signature_name: "Alex Operator", signed_at: "2026-08-20T12:00:00Z" } });
  });

  it("replaces completion checkboxes with a validated in-portal personal information form", async () => {
    const user = userEvent.setup(); renderPortal();
    await screen.findByRole("heading", { name: "Welcome, Alex" });
    expect(screen.getByText("Alex Operator")).toBeInTheDocument();
    expect(screen.getByText("alex.operator@example.com")).toBeInTheDocument();
    await user.type(screen.getByRole("textbox", { name: "Mobile phone" }), "250-555-0114");
    await user.type(screen.getByLabelText("Date of birth"), "1990-01-02");
    await user.click(screen.getByRole("button", { name: "Save and continue" }));
    await waitFor(() => expect(employeeOnboardingApi.savePortalProgress).toHaveBeenCalledWith("secure-token", expect.objectContaining({ personal_information: { preferred_name: "Alex", mobile_phone: "250-555-0114", date_of_birth: "1990-01-02" } })));
    expect(await screen.findByRole("heading", { name: "Home address" })).toBeInTheDocument();
  });

  it("submits only after all saved forms, acknowledgement, and typed signature", async () => {
    const user = userEvent.setup();
    vi.mocked(employeeOnboardingApi.portalRecord).mockResolvedValue({ onboarding: invitationRecord, packet: completePacket });
    renderPortal();
    await user.click(await screen.findByRole("button", { name: /Review and submit/ }));
    const submit = screen.getByRole("button", { name: "Submit for management review" });
    expect(submit).toBeDisabled();
    await user.click(screen.getByRole("checkbox", { name: /I certify that the information I provided/i }));
    await user.type(screen.getByRole("textbox", { name: /Electronic signature/i }), "Alex Operator");
    expect(submit).toBeEnabled();
    await user.click(submit);
    await waitFor(() => expect(employeeOnboardingApi.submitPortal).toHaveBeenCalledWith("secure-token", completePacket, true, "Alex Operator"));
    expect(await screen.findByText("Submitted for review")).toBeInTheDocument();
  });

  it("requires the 2026 federal TD1 world-income answer for a non-resident", async () => {
    const user = userEvent.setup();
    renderPortal();
    await user.click(await screen.findByRole("button", { name: /2026 TD1 tax forms/ }));
    await user.type(screen.getByLabelText("Social Insurance Number"), "046454286");
    const country = screen.getByRole("textbox", { name: "Country of permanent residence" });
    await user.clear(country);
    await user.type(country, "United States");
    expect(screen.getByText(/Will 90% or more of your world income/)).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: "No" }));
    await user.click(screen.getByRole("checkbox", { name: /federal TD1 information is correct/ }));
    await user.click(screen.getByRole("checkbox", { name: /British Columbia TD1BC information is correct/ }));
    await user.click(screen.getByRole("button", { name: "Save and continue" }));
    await waitFor(() => expect(employeeOnboardingApi.savePortalProgress).toHaveBeenCalledWith(
      "secure-token",
      expect.objectContaining({
        tax_forms: expect.objectContaining({
          country_of_permanent_residence: "United States",
          non_resident_world_income_90_percent_or_more: false,
          federal_claim_amounts: Array(12).fill("0"),
        }),
      }),
    ));
  });
});
