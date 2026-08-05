import AxeBuilder from "@axe-core/playwright";
import { expect, Page, test } from "@playwright/test";

const user = {
  id: "00000000-0000-0000-0000-000000000214",
  email: "release-gate@ironhousecontracting.com",
  display_name: "Release Gate Operator",
  role: "admin",
  is_active: true,
  password_reset_required: false,
  last_login_at: null,
  created_at: "2026-07-14T00:00:00Z",
  updated_at: "2026-07-14T00:00:00Z",
};

async function mockApi(page: Page) {
  let authenticated = false;
  await page.route("http://localhost:8000/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/auth/me")) {
      await route.fulfill(
        authenticated
          ? { status: 200, json: { authentication: "authenticated", user } }
          : { status: 401, json: { detail: "Sign in is required." } },
      );
      return;
    }
    if (path.endsWith("/auth/login") && request.method() === "POST") {
      authenticated = true;
      await route.fulfill({ status: 200, json: { authentication: "authenticated", user } });
      return;
    }
    if (path.endsWith("/auth/me/permissions")) {
      await route.fulfill({ status: 200, json: { role: "admin", modules: { projects: ["read", "write"], suppliers: ["read", "write"], equipment: ["read", "write"] } } });
      return;
    }
    if (path.endsWith("/users/governance")) {
      await route.fulfill({
        status: 200,
        json: {
          generated_at: "2026-07-24T00:00:00Z",
          canonical_email_domain: "ironhousecontracting.com",
          summary: {
            total_accounts: 1,
            active_accounts: 1,
            active_administrators: 1,
            legacy_domain_accounts: 0,
            accounts_requiring_review: 1,
            critical_findings: 0,
          },
          accounts: [{ ...user, review_reasons: ["Only active administrator"] }],
          findings: [{
            code: "single_active_administrator",
            severity: "high",
            title: "Single active administrator",
            recommendation: "Approve and provision a second named administrator.",
            account_ids: [user.id],
          }],
        },
      });
      return;
    }
    if (path.endsWith("/field-operations/bootstrap")) {
      await route.fulfill({
        status: 200,
        json: {
          employees: [], projects: [], suppliers: [], equipment: [], cost_codes: [],
          job_workbooks: [], production_items: [], material_types: [], material_movement_summary: [],
          milestone_catalog: [], milestone_recognitions: [], paperwork_recognitions: [],
          vehicles: [], vehicle_logs: [], time_entries: [], records: [], certifications: [], alerts: [],
          toolbox_talk: { week_of: "2026-08-02", title: "Release gate", summary: "Staging-only QA", discussion_points: [], source_name: "WorkSafeBC", source_url: "https://www.worksafebc.com/" },
          flha_presets: [],
        },
      });
      return;
    }
    if (path.endsWith("/daily-timesheets/bootstrap")) {
      await route.fulfill({
        status: 200,
        json: {
          projects: [{ id: "11500000-0000-0000-0000-000000000001", name: "Granite Creek Civil Works", project_number: "IH-115", status: "construction" }],
          employees: [
            { id: "11500000-0000-0000-0000-000000000002", code: "EMP-FRM115", name: "Fran Foreman", classification: "Foreman", portal_role: "foreman" },
            { id: "11500000-0000-0000-0000-000000000003", code: "EMP-CRW115", name: "Casey Crew", classification: "Pipe Layer", portal_role: "employee" },
          ],
          equipment: [{ id: "11500000-0000-0000-0000-000000000004", name: "Excavator", identifier: "EX-115", status: "available" }],
          rentals: [],
          vendors: [{ id: "11500000-0000-0000-0000-000000000005", name: "Active Aggregate", category: "materials" }],
          receipts: [{ id: "11500000-0000-0000-0000-000000000006", reference: "R-115", vendor_name: "Active Aggregate", receipt_date: "2026-08-02", status: "approved" }],
          project_cost_codes: { "11500000-0000-0000-0000-000000000001": [{ code: "03-100", name: "Excavation" }, { code: "31-200", name: "Pipe installation" }] },
          assigned_crew: { "11500000-0000-0000-0000-000000000001": ["11500000-0000-0000-0000-000000000003"] },
          sheets: [],
          can_approve: true,
        },
      });
      return;
    }
    if (path.endsWith("/daily-timesheets") && request.method() === "POST") {
      const payload = request.postDataJSON();
      await route.fulfill({
        status: 201,
        json: {
          id: "11500000-0000-0000-0000-000000000007", status: "draft", version: 1,
          project_id: payload.project_id, work_date: payload.work_date, shift: payload.shift,
          details: payload, document_ids: payload.document_ids, submitted_by: user.email,
          created_at: "2026-08-02T00:00:00Z", updated_at: "2026-08-02T00:00:00Z",
        },
      });
      return;
    }
    if (path.endsWith("/backups")) {
      if (request.method() === "GET") {
        await route.fulfill({ status: 200, json: { items: [], total: 0 } });
        return;
      }
      await route.fulfill({ status: 201, json: { id: "15400000-0000-0000-0000-000000000001", media_asset_id: "15400000-0000-0000-0000-000000000002", media_sha256: "a".repeat(64), uploader_id: user.id, uploader_email: user.email, uploader_role: user.role, uploaded_at: "2026-08-05T14:24:59Z", note: "Packing slip backup", project_hint: "Granite Creek", status: "pending", detected_type: null, confidence: null, destination_type: null, destination_record_id: null, error: null, sensitive_quarantine: false, classifier: null, attempt_count: 0, audit_history: [] } });
      return;
    }
    if (path.endsWith("/finance/startup-expenses")) {
      await route.fulfill({
        status: 200,
        json: {
          total_startup_costs: 0,
          owner_loan_payable: 0,
          reimbursed_to_owner: 0,
          pending_review: 0,
          approved_unreimbursed: 0,
          entries: [],
        },
      });
      return;
    }
    if (path.endsWith("/finance/receipts")) {
      await route.fulfill({ status: 200, json: { items: [], total: 0 } });
      return;
    }
    if (path.endsWith("/estimates/rate-library")) {
      await route.fulfill({ status: 200, json: { production_rates: [] } });
      return;
    }
    if (path.endsWith("/meeting-minutes/status")) {
      await route.fulfill({
        status: 200,
        json: {
          enabled: true,
          configured: true,
          transcription_model: "gpt-4o-mini-transcribe",
          summary_model: "gpt-5.6-sol",
          max_audio_bytes: 26214400,
          audio_retained: false,
        },
      });
      return;
    }
    if (path.endsWith("/meeting-minutes")) {
      await route.fulfill({ status: 200, json: [] });
      return;
    }
    if (path.endsWith("/google-calendar/status")) {
      await route.fulfill({
        status: 200,
        json: {
          enabled: true,
          configured: true,
          connected: true,
          status: "connected",
          required_scope: "https://www.googleapis.com/auth/calendar.events.owned",
          last_synced_at: null,
          last_error: null,
        },
      });
      return;
    }
    if (path.endsWith("/google-calendar/events")) {
      await route.fulfill({ status: 200, json: [] });
      return;
    }
    await route.fulfill({ status: 200, json: { items: [], total: 0 } });
  });
}

async function signIn(page: Page) {
  await page.goto("/");
  await page.getByLabel("Email").fill("release-gate@ironhousecontracting.com");
  await page.getByLabel("Password").fill("Local-release-gate-only");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Iron House Dashboard" })).toBeVisible();
}

async function expectNoSeriousAccessibilityViolations(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const blocking = results.violations.filter(
    ({ impact }) => impact === "critical" || impact === "serious",
  );
  expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
}

function isMobileProject(projectName: string) {
  return projectName === "mobile-chromium" || projectName === "ipad-webkit";
}

test("authenticated core shell is responsive and accessible", async ({ page }, testInfo) => {
  await mockApi(page);
  await signIn(page);
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(hasHorizontalOverflow).toBe(false);

  if (isMobileProject(testInfo.project.name)) {
    const menu = page.getByRole("button", { name: "Open navigation" });
    await expect(menu).toBeVisible();
    await menu.click();
    await expect(page.getByRole("navigation").getByText("Dashboard", { exact: true })).toBeVisible();
  } else {
    await expect(page.getByText("Administrator access")).toBeVisible();
  }

  await expectNoSeriousAccessibilityViolations(page);
});

test("receipt capture and financial review surfaces pass responsive accessibility QA", async ({ page }) => {
  await mockApi(page);
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await signIn(page);

  await page.goto("/employee-portal/receipts");
  await expect(page.getByRole("heading", { name: "Employee Portal" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Submit a receipt" })).toBeVisible();
  await expect(page.getByText("Receipt photos (camera or gallery, up to 10 pages)")).toBeVisible();
  await expect(page.getByRole("button", { name: "Extract receipt" })).toBeDisabled();
  await expectNoSeriousAccessibilityViolations(page);

  await page.goto("/finance");
  await expect(page.getByRole("heading", { name: "Financial Control" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Receipt review and coding" })).toBeVisible();
  await expect(page.getByText("Nothing posts automatically.")).toHaveCount(0);
  await expectNoSeriousAccessibilityViolations(page);
  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(hasHorizontalOverflow).toBe(false);
  expect(pageErrors).toEqual([]);
});

test("Backups saves one photo on phone, iPad, and desktop without approval", async ({ page }) => {
  await mockApi(page);
  await signIn(page);
  await page.goto("/backups");
  await expect(page.getByRole("heading", { name: "Backups" })).toBeVisible();
  const picker = page.getByLabel("Take photo or choose image");
  await picker.setInputFiles({
    name: "packing-slip.jpg",
    mimeType: "image/jpeg",
    buffer: Buffer.from("disposable acceptance image"),
  });
  await page.getByLabel("Optional note").fill("Packing slip backup");
  await page.getByLabel("Optional project hint").fill("Granite Creek");
  await page.getByRole("button", { name: "Save original" }).click();
  await expect(page.getByRole("status")).toContainText("Original saved");
  await expect(page.getByText("pending", { exact: true })).toBeVisible();
  const overflow = await page.evaluate(() => ({
    width: document.documentElement.scrollWidth,
    viewport: document.documentElement.clientWidth,
  }));
  expect(overflow.width).toBe(overflow.viewport);
  await expectNoSeriousAccessibilityViolations(page);
});

test("foreman daily time sheet passes responsive interaction and accessibility QA", async ({ page }) => {
  await mockApi(page);
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await signIn(page);

  await page.goto("/foreman-portal/time");
  await expect(page.getByRole("heading", { name: "Foreman Portal" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Foreman Daily Time Sheet" })).toBeVisible();

  await page.getByLabel("Job number and name").selectOption("11500000-0000-0000-0000-000000000001");
  await page.getByLabel("Foreman / supervisor").selectOption("11500000-0000-0000-0000-000000000002");
  await expect(page.getByText("EMP-CRW115 · Casey Crew")).toBeVisible();
  await page.getByLabel("Job cost code").selectOption("03-100");
  await page.getByLabel("ST", { exact: true }).fill("8");
  await expect(page.getByText("ST 8.00 · OT 0.00 · 8.00 hours")).toBeVisible();
  await expect(page.getByRole("button", { name: "Submit" })).toBeEnabled();

  await expect.poll(async () => page.evaluate((key) => Boolean(localStorage.getItem(key)), "ihos:foreman-daily-timesheet:v1:" + user.id)).toBe(true);
  expect(await page.evaluate(() => localStorage.getItem("ihos:foreman-daily-timesheet:v1"))).toBeNull();

  const overflow = await page.evaluate(() => ({
    width: document.documentElement.scrollWidth,
    viewport: document.documentElement.clientWidth,
  }));
  expect(overflow.width).toBe(overflow.viewport);
  await expectNoSeriousAccessibilityViolations(page);
  expect(pageErrors).toEqual([]);
});

const tabs = [
  ["Dashboard", "Iron House Dashboard"],
  ["Backups", "Backups"],
  ["Meeting Minutes", "Meeting Minutes"],
  ["Google Calendar", "Google Calendar"],
  ["MVP Workflow", "IHOS MVP Workflow"],
  ["Project Operations", "Project Operations"],
  ["Document Operations", "Document Operations"],
  ["Projects", "Project Workspace"],
  ["RFQ Builder", "RFQ Package Builder"],
  ["Supplier Database", "Supplier Database"],
  ["Estimating", "Estimating"],
  ["Drawing Intelligence", "Drawing Intelligence"],
  ["Quantity Takeoff Engine", "Quantity Takeoff Engine"],
  ["Municipality Intelligence", "Municipality Intelligence"],
  ["Quote Comparison", "Quote Comparison"],
  ["Tender Tracker", "Tender Intake"],
  ["Document Library", "Document Library"],
  ["Equipment", "Equipment"],
  ["Reporting", "Reporting"],
  ["Settings", "Settings"],
] as const;

test("every navigation tab opens a real responsive screen", async ({ page }, testInfo) => {
  test.slow();
  await mockApi(page);
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await signIn(page);

  for (const [label, heading] of tabs) {
    if (isMobileProject(testInfo.project.name)) {
      const menu = page.getByRole("button", { name: "Open navigation" });
      if (await menu.isVisible()) await menu.click();
    }
    await page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: label, exact: true }).click();
    await expect(page.getByRole("heading", { name: heading, exact: true }).first()).toBeVisible();
    await page.waitForTimeout(350);
    await expect(page.getByText("Phase 2 expansion point")).toHaveCount(0);
    await expect(page.getByText(/Request failed with 5\d\d|Unable to load .*\(5\d\d\)/)).toHaveCount(0);
    const overflow = await page.evaluate(() => ({
      page: [document.documentElement.scrollWidth, document.documentElement.clientWidth],
      elements: Array.from(document.querySelectorAll("body *"))
        .filter((element) => element.getBoundingClientRect().right > document.documentElement.clientWidth + 1)
        .slice(0, 8)
        .map((element) => ({ tag: element.tagName, className: element.className, right: Math.round(element.getBoundingClientRect().right) })),
    }));
    expect(overflow.page[0], `${label} overflow: ${JSON.stringify(overflow.elements)}`).toBe(overflow.page[1]);
    await expectNoSeriousAccessibilityViolations(page);
  }

  expect(pageErrors).toEqual([]);
});
