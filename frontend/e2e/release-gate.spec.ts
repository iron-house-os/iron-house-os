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
    await route.fulfill({ status: 200, json: { items: [], total: 0 } });
  });
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
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Iron House OS" })).toBeVisible();
  await page.getByLabel("Email").fill("release-gate@ironhousecivil.com");
  await page.getByLabel("Password").fill("Local-release-gate-only");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByRole("heading", { name: "Iron House Dashboard" })).toBeVisible();
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
