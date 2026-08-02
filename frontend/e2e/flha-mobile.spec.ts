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

async function mockFlhaApi(page: Page) {
  await page.route("http://localhost:8000/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/auth/me")) return route.fulfill({ status: 200, json: { authentication: "authenticated", user } });
    if (path.endsWith("/field-operations/bootstrap")) return route.fulfill({ status: 200, json: {
      employees: [employee], projects: [{ id: "20000000-0000-0000-0000-000000000113", name: "River Road", project_number: "113", status: "active" }],
      suppliers: [], equipment: [], cost_codes: [], job_workbooks: [], production_items: [], material_types: [], material_movement_summary: [],
      milestone_catalog: [], milestone_recognitions: [], paperwork_recognitions: [], vehicles: [], vehicle_logs: [], time_entries: [], records: [], certifications: [], alerts: [],
      toolbox_talk: { week_of: "2026-08-02", title: "Field communication", summary: "Review communication expectations.", discussion_points: [], source_name: "WorkSafeBC", source_url: "https://www.worksafebc.com" },
      flha_presets: [{ id: "company-excavation", scope: "company", name: "Excavation and utility work", rows: [{ task: "Excavate", hazard: "Utility contact", control: "Confirm current locates", control_level: "engineering", risk: "critical", evidence_required: true }] }],
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
