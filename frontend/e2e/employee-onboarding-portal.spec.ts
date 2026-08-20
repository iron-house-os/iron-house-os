import { expect, test } from "@playwright/test";

const onboarding = {
  id: "00000000-0000-0000-0000-000000000229",
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
  missing_items: [],
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

const emptyPacket = {
  personal_information: null,
  address: null,
  emergency_contact: null,
  payroll: null,
  tax_forms: null,
  employment_agreements: null,
  certifications: null,
  ppe_requirements: null,
  signature_name: null,
  signed_at: null,
};

test("invited employee completes actual IHOS forms on a mobile-safe portal", async ({ page }) => {
  await page.route("**/api/v1/employee-onboarding/portal/secure-token**", async (route) => {
    if (route.request().method() === "PUT") {
      const payload = route.request().postDataJSON() as { packet: typeof emptyPacket };
      await route.fulfill({ json: { onboarding: { ...onboarding, completion_percent: 11 }, packet: payload.packet } });
      return;
    }
    await route.fulfill({ json: { onboarding, packet: emptyPacket } });
  });

  await page.goto("/employee-onboarding/secure-token");
  await expect(page.getByRole("heading", { name: "Welcome, Alex" })).toBeVisible();
  await expect(page.getByText("Personal, banking, SIN, and tax values are encrypted before storage.")).toBeVisible();
  await page.getByRole("textbox", { name: "Mobile phone" }).fill("250-555-0114");
  await page.getByLabel("Date of birth").fill("1990-01-02");
  await page.getByRole("button", { name: "Save and continue" }).click();
  await expect(page.getByRole("heading", { name: "Home address" })).toBeVisible();
  await expect(page.getByText("1 of 8 forms saved")).toBeVisible();
  await expect(page.locator("body")).not.toHaveCSS("overflow-x", "scroll");
});
