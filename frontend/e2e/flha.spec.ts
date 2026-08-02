import AxeBuilder from "@axe-core/playwright";
import { expect, Page, test } from "@playwright/test";

const user = {
  id: "00000000-0000-0000-0000-000000000301",
  email: "flha.qa@ironhousecontracting.com",
  display_name: "FLHA QA Foreperson",
  role: "admin",
  is_active: true,
  password_reset_required: false,
  last_login_at: null,
  created_at: "2026-08-02T00:00:00Z",
  updated_at: "2026-08-02T00:00:00Z",
};
const employee = {
  id: "00000000-0000-0000-0000-000000000302",
  first_name: "FLHA",
  last_name: "Foreperson",
  email: user.email,
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
};
const project = { id: "00000000-0000-0000-0000-000000000303", name: "WebKit FLHA Project" };

function bootstrap(records: unknown[]) {
  return {
    employees: [employee],
    projects: [project],
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
    records,
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
  };
}

async function mockApi(page: Page) {
  let authenticated = false;
  let record: Record<string, unknown> | null = null;
  await page.route("http://localhost:8000/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/auth/me")) {
      await route.fulfill(authenticated
        ? { status: 200, json: { authentication: "authenticated", user } }
        : { status: 401, json: { detail: "Sign in is required." } });
      return;
    }
    if (path.endsWith("/auth/login")) {
      authenticated = true;
      await route.fulfill({ status: 200, json: { authentication: "authenticated", user } });
      return;
    }
    if (path.endsWith("/auth/me/permissions")) {
      await route.fulfill({ status: 200, json: { role: "admin", modules: { "field-operations": ["read", "write"], media: ["read", "write"] } } });
      return;
    }
    if (path.endsWith("/field-operations/bootstrap")) {
      await route.fulfill({ status: 200, json: bootstrap(record ? [record] : []) });
      return;
    }
    if (path.endsWith("/field-operations/flha") && request.method() === "POST") {
      const body = request.postDataJSON();
      record = {
        id: "00000000-0000-0000-0000-000000000304",
        record_type: "daily_hazard_assessment",
        project_id: body.project_id,
        employee_id: employee.id,
        equipment_id: null,
        supplier_id: null,
        cost_code: null,
        work_date: body.work_date,
        title: body.title,
        status: "draft",
        severity: "none",
        details: {
          ...body.details,
          flha_version: 1,
          root_record_id: "00000000-0000-0000-0000-000000000304",
          source_record_id: null,
          release_blockers: [],
          ai_advisory_only: true,
          audit_trail: [{ action: "created", actor_email: user.email, timestamp: "2026-08-02T00:00:00Z" }],
        },
        document_ids: [],
        signatures: [],
        alert_recipients: [],
        submitted_by: user.email,
      };
      await route.fulfill({ status: 201, json: record });
      return;
    }
    if (path.endsWith("/release") && request.method() === "POST") {
      record = {
        ...record!,
        status: "released",
        details: {
          ...(record!.details as object),
          released_by: user.email,
          released_at: "2026-08-02T00:01:00Z",
        },
      };
      await route.fulfill({ status: 200, json: record });
      return;
    }
    if (path.endsWith("/sign") && request.method() === "POST") {
      record = {
        ...record!,
        status: "signed",
        signatures: [{
          employee_id: employee.id,
          employee_name: "FLHA Foreperson",
          signed_at: "2026-08-02T00:02:00Z",
          signed_by_account: user.email,
        }],
      };
      await route.fulfill({ status: 200, json: record });
      return;
    }
    if (path.endsWith("/media")) {
      await route.fulfill({ status: 200, json: [] });
      return;
    }
    await route.fulfill({ status: 200, json: { items: [], total: 0 } });
  });
}

async function signIn(page: Page) {
  await page.goto("/");
  await page.getByLabel("Email").fill(user.email);
  await page.getByLabel("Password").fill("Disposable-FLHA-QA-only");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Iron House Dashboard" })).toBeVisible();
}

test("FLHA completes, releases and signs without overflow or accessibility blockers", async ({ page }, testInfo) => {
  await mockApi(page);
  await signIn(page);
  if (testInfo.project.name !== "desktop-chromium") {
    await page.getByRole("button", { name: "Open navigation" }).click();
  }
  await page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "Daily FLHA" }).click();
  await expect(page.getByRole("heading", { name: "Field Level Hazard Assessment" })).toBeVisible();

  await page.getByLabel("Site / location").fill("North tie-in");
  await page.getByLabel("Weather / conditions").fill("Dry, 18 C");
  await page.getByLabel("Supervisor / foreperson").fill("FLHA QA Foreperson");
  await page.getByLabel("First aid attendant").fill("FLHA QA Foreperson");
  for (const button of await page.getByRole("button", { name: "yes", exact: true }).all()) await button.click();
  await page.getByLabel("Task").fill("Excavate utility trench");
  await page.getByLabel("Hazard").fill("Cave-in and utility strike");
  await page.getByLabel("Control").fill("Verify locates, shoring, ladder access and exclusion zone");
  await page.getByLabel("Responsible person").fill("FLHA QA Foreperson");
  await page.getByLabel("Critical hazard").check();
  await page.getByLabel("Field control accepted").check();
  await page.getByLabel("Emergency response").fill("Stop work, call emergency services and notify supervision");
  await page.getByLabel("Muster point").fill("Site entrance");
  await page.getByLabel("Communication").fill("Radio channel 2");

  await page.getByRole("button", { name: "Create FLHA draft" }).click();
  await expect(page.getByText("FLHA draft saved.")).toBeVisible();
  await expect(page.getByText("FLHA photos / evidence")).toBeVisible();
  await page.getByRole("button", { name: /Verify field conditions and release/ }).click();
  await expect(page.getByText(/Supervisor release recorded/)).toBeVisible();
  await page.getByRole("button", { name: "Review and sign" }).click();
  await expect(page.getByText(/Crew acknowledgement recorded/)).toBeVisible();
  await expect(page.getByText("Signed", { exact: true })).toBeVisible();

  const overflow = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(overflow.scrollWidth).toBe(overflow.clientWidth);
  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(
    accessibility.violations.filter(({ impact }) => impact === "critical" || impact === "serious"),
    JSON.stringify(accessibility.violations, null, 2),
  ).toEqual([]);
});

