import AxeBuilder from "@axe-core/playwright";
import { expect, Page, test } from "@playwright/test";

const user = {
  id: "00000000-0000-0000-0000-000000000214",
  email: "release-gate@ironhousecivil.com",
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
    if (path.endsWith("/estimates/rate-library")) {
      await route.fulfill({ status: 200, json: { production_rates: [] } });
      return;
    }
    await route.fulfill({ status: 200, json: { items: [], total: 0 } });
  });
}

async function signIn(page: Page) {
  await page.goto("/");
  await page.getByLabel("Email").fill("release-gate@ironhousecivil.com");
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

test("authenticated core shell is responsive and accessible", async ({ page }, testInfo) => {
  await mockApi(page);
  await signIn(page);
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(hasHorizontalOverflow).toBe(false);

  if (testInfo.project.name === "mobile-chromium") {
    const menu = page.getByRole("button", { name: "Open navigation" });
    await expect(menu).toBeVisible();
    await menu.click();
    await expect(page.getByRole("navigation").getByText("Dashboard", { exact: true })).toBeVisible();
  } else {
    await expect(page.getByText("Administrator access")).toBeVisible();
  }

  await expectNoSeriousAccessibilityViolations(page);
});

const tabs = [
  ["Dashboard", "Iron House Dashboard"],
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
  await mockApi(page);
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await signIn(page);

  for (const [label, heading] of tabs) {
    if (testInfo.project.name === "mobile-chromium") {
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
