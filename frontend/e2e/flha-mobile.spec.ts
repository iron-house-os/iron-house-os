import AxeBuilder from "@axe-core/playwright";
import { expect, Page, test } from "@playwright/test";

const user = {
  id: "00000000-0000-0000-0000-000000000113", email: "foreperson@ironhousecontracting.com",
  display_name: "Field Foreperson", role: "admin", is_active: true, password_reset_required: false,
  last_login_at: null, created_at: "2026-08-02T00:00:00Z", updated_at: "2026-08-02T00:00:00Z",
};
const employee = {
  id: "10000000-0000-0000-0000-000000000113", first_name: "Field", last_name: "Foreperson",
  email: user.email, role: "Foreperson", phone: null, address: null, emergency_contact_name: null,
  emergency_contact_phone: null, emergency_contact_relationship: null, hire_date: null,
  portal_role: "foreman", notes: null, status: "active", created_at: "2026-08-02T00:00:00Z", updated_at: "2026-08-02T00:00:00Z",
};
const emergencyCard = {
  id: "30000000-0000-0000-0000-000000000113", record_type: "emergency_action_card",
  project_id: null, employee_id: null, equipment_id: null, supplier_id: null, cost_code: null,
  work_date: "2026-08-18", title: "River Road emergency card", status: "ready", severity: "medium",
  details: { project: "River Road", address: "100 River Road", muster: "North gate", firstAid: "Site office", emergencyLead: "Site supervisor", rescue: "Stop work and report to muster point" },
  document_ids: [], signatures: [], alert_recipients: [], submitted_by: user.email,
};

async function mockFlhaApi(page: Page) {
  await page.route("http://localhost:8000/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/auth/me")) return route.fulfill({ status: 200, json: { authentication: "authenticated", user } });
    if (path.endsWith("/field-operations/bootstrap")) return route.fulfill({ status: 200, json: {
      employees: [employee], projects: [{ id: "20000000-0000-0000-0000-000000000113", name: "River Road", project_number: "113", status: "active" }],
      suppliers: [], equipment: [], cost_codes: [], job_workbooks: [], production_items: [], material_types: [], material_movement_summary: [],
      milestone_catalog: [], milestone_recognitions: [], paperwork_recognitions: [], vehicles: [], vehicle_logs: [], time_entries: [], records: [emergencyCard], certifications: [], alerts: [],
      toolbox_talk: { week_of: "2026-08-02", title: "Field communication", summary: "Review communication expectations.", discussion_points: [], source_name: "WorkSafeBC", source_url: "https://www.worksafebc.com" },
      flha_presets: [{ id: "company-excavation", scope: "company", name: "Excavation and utility work", rows: [{ task: "Excavate", hazard: "Utility contact", control: "Confirm current locates", control_level: "engineering", risk: "critical", evidence_required: true }] }],
    } });
    if (path.endsWith("/field-operations/safety/analytics")) return route.fulfill({ status: 200, json: {
      as_of: "2026-08-18", safety_controls_total: 1, blocked_permits: 0, at_risk_permits: 0,
      open_corrective_actions: 0, overdue_corrective_actions: 0, active_emergency_cards: 1,
      flha_last_30_days: 0, toolbox_talks_last_30_days: 0, open_incidents: 0,
      credentials_expiring_60_days: 0, credentials_expired: 0, audit_export_records: 1,
      confidential_record_types_excluded: ["first_aid_record", "incident"],
    } });
    return route.fulfill({ status: 200, json: { items: [], total: 0 } });
  });
}

test("FLHA keeps field controls touchable, complete, and within the viewport", async ({ page }) => {
  await mockFlhaApi(page);
  await page.goto("/foreman-portal/safety");
  await expect(page.getByRole("heading", { name: "Daily FLHA" })).toBeVisible();
  await expect(page.getByText("Underground utilities and current locates")).toBeVisible();
  await expect(page.getByText("Emergency response and stop-work")).toBeVisible();
  await page.getByRole("button", { name: "Add Excavation and utility work" }).click();
  await expect(page.getByText(/Blocked: 1 critical hazard/)).toBeVisible();
  const sizes = await page.locator("form").filter({ hasText: "Daily FLHA" }).locator("button").evaluateAll((buttons) => buttons.filter((button) => button.offsetParent !== null).map((button) => ({ width: button.getBoundingClientRect().width, height: button.getBoundingClientRect().height, text: button.textContent })));
  expect(sizes.filter((item) => item.height < 44), JSON.stringify(sizes.filter((item) => item.height < 44))).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
  const serious = (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze()).violations.filter((item) => item.impact === "critical" || item.impact === "serious");
  expect(serious, JSON.stringify(serious, null, 2)).toEqual([]);
  if (process.env.FLHA_SCREENSHOT_PATH) await page.screenshot({ path: process.env.FLHA_SCREENSHOT_PATH, fullPage: true });
});

test("emergency card deep link is QR-ready, offline-downloadable, and mobile-safe", async ({ page }) => {
  await mockFlhaApi(page);
  await page.goto(`/safety-operations?view=emergency&record=${emergencyCard.id}`);
  await expect(page.getByRole("heading", { name: "Safety Operations Control" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "River Road" })).toBeVisible();
  await expect(page.getByRole("link", { name: "PDF / save offline" })).toHaveAttribute("href", /emergency-action-card\.pdf$/);
  await page.getByText("Show QR field link").click();
  await expect(page.getByRole("img", { name: "QR field link for River Road" })).toHaveAttribute("src", /^data:image\/svg\+xml/);
  await expect(page.getByText(/no password or access token/i)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
  const serious = (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze()).violations.filter((item) => item.impact === "critical" || item.impact === "serious");
  expect(serious, JSON.stringify(serious, null, 2)).toEqual([]);
});
