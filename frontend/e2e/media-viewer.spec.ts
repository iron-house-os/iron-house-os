import AxeBuilder from "@axe-core/playwright";
import { expect, Page, test } from "@playwright/test";

const user = {
  id: "00000000-0000-0000-0000-000000000112",
  email: "media-acceptance@ironhousecontracting.com",
  display_name: "Media Acceptance Operator",
  role: "admin",
  is_active: true,
  password_reset_required: false,
  last_login_at: null,
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
};

const equipmentId = "00000000-0000-0000-0000-000000000201";
const assetId = "00000000-0000-0000-0000-000000000202";
const originalVersionId = "00000000-0000-0000-0000-000000000203";
const image = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
  "base64",
);

type Version = {
  id: string;
  asset_id: string;
  parent_version_id: string | null;
  document_id: string;
  version_number: number;
  action: "original" | "edit" | "restore";
  editor_id: string;
  editor_email: string;
  operations: Array<{ type: string; values: Record<string, unknown> }>;
  change_summary: string;
  amendment_reason: null;
  created_at: string;
};

function originalVersion(): Version {
  return {
    id: originalVersionId,
    asset_id: assetId,
    parent_version_id: null,
    document_id: "00000000-0000-0000-0000-000000000204",
    version_number: 1,
    action: "original",
    editor_id: user.id,
    editor_email: user.email,
    operations: [],
    change_summary: "Original upload retained as immutable evidence.",
    amendment_reason: null,
    created_at: "2026-08-01T00:00:00Z",
  };
}

async function mockMediaApi(page: Page) {
  let authenticated = false;
  let asset = {
    id: assetId,
    original_document_id: "00000000-0000-0000-0000-000000000204",
    current_version_id: originalVersionId,
    project_id: null,
    caption: "Excavator inspection",
    captured_date: "2026-08-01",
    location: "Authorized yard",
    category: "equipment",
    controlled: false,
    created_by_email: user.email,
    versions: [originalVersion()],
    links: [{ record_type: "equipment", record_id: equipmentId }],
    created_at: "2026-08-01T00:00:00Z",
    updated_at: "2026-08-01T00:00:00Z",
  };

  await page.route("http://localhost:8000/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() === "OPTIONS") {
      await route.fulfill({
        status: 204,
        headers: {
          "Access-Control-Allow-Credentials": "true",
          "Access-Control-Allow-Headers": "content-type",
          "Access-Control-Allow-Methods": "GET,POST,PATCH,OPTIONS",
          "Access-Control-Allow-Origin": "http://127.0.0.1:4173",
        },
      });
      return;
    }
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
      await route.fulfill({ status: 200, json: { role: "admin", modules: { equipment: ["read", "write"], media: ["read", "write"] } } });
      return;
    }
    if (path.endsWith("/equipment")) {
      await route.fulfill({
        status: 200,
        json: {
          items: [{
            id: equipmentId,
            name: "Acceptance Excavator",
            equipment_type: "Excavator",
            identifier: "EX-112",
            status: "available",
            hourly_rate: 185,
            created_at: "2026-08-01T00:00:00Z",
            updated_at: "2026-08-01T00:00:00Z",
          }],
          total: 1,
        },
      });
      return;
    }
    if (path.endsWith(`/${assetId}/content`)) {
      await route.fulfill({
        status: 200,
        body: image,
        contentType: "image/png",
        headers: {
          "Access-Control-Allow-Credentials": "true",
          "Access-Control-Allow-Origin": "http://127.0.0.1:4173",
        },
      });
      return;
    }
    if (path.endsWith(`/${assetId}/versions`) && request.method() === "POST") {
      const version: Version = {
        ...originalVersion(),
        id: "00000000-0000-0000-0000-000000000205",
        parent_version_id: asset.current_version_id,
        document_id: "00000000-0000-0000-0000-000000000206",
        version_number: 2,
        action: "edit",
        operations: [{ type: "rotate", values: { degrees: 90 } }],
        change_summary: "Photo correction and annotation",
        created_at: "2026-08-01T00:01:00Z",
      };
      asset = { ...asset, current_version_id: version.id, versions: [version, ...asset.versions] };
      await route.fulfill({ status: 200, json: asset });
      return;
    }
    if (path.endsWith(`/${assetId}/restore`) && request.method() === "POST") {
      const version: Version = {
        ...originalVersion(),
        id: "00000000-0000-0000-0000-000000000207",
        parent_version_id: asset.current_version_id,
        version_number: 3,
        action: "restore",
        change_summary: "Restored version 1.",
        created_at: "2026-08-01T00:02:00Z",
      };
      asset = { ...asset, current_version_id: version.id, versions: [version, ...asset.versions] };
      await route.fulfill({ status: 200, json: asset });
      return;
    }
    if (path.endsWith("/media")) {
      await route.fulfill({ status: 200, json: [asset] });
      return;
    }
    await route.fulfill({ status: 200, json: { items: [], total: 0 } });
  });
}

async function signIn(page: Page) {
  await page.goto("/");
  await page.getByLabel("Email").fill(user.email);
  await page.getByLabel("Password").fill("Disposable-media-acceptance-only");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Iron House Dashboard" })).toBeVisible();
}

test("photo viewer opens, saves an edit, shows history, and restores", async ({ page }) => {
  await mockMediaApi(page);
  await signIn(page);
  await page.goto("/equipment");
  await page.getByAltText("Excavator inspection").click();

  const dialog = page.getByRole("dialog", { name: "Photo viewer and editor" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText("Version 1 · original always retained")).toBeVisible();
  await dialog.getByRole("button", { name: "Rotate" }).click();
  await dialog.getByRole("button", { name: "Save as new version" }).click();
  await expect(dialog.getByText("Version 2 · original always retained")).toBeVisible();

  await dialog.getByRole("button", { name: "history" }).click();
  await expect(dialog.getByText("Version 2", { exact: true })).toBeVisible();
  await expect(dialog.getByText("Version 1", { exact: true })).toBeVisible();
  await dialog.getByRole("button", { name: "Restore as new version" }).click();
  await expect(dialog.getByText("Version 3", { exact: true })).toBeVisible();
  await expect(dialog.getByText("restore", { exact: true })).toBeVisible();

  const overflow = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(overflow.scrollWidth).toBe(overflow.clientWidth);
  const accessibility = await new AxeBuilder({ page })
    .include('[role="dialog"]')
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(
    accessibility.violations.filter(({ impact }) => impact === "critical" || impact === "serious"),
    JSON.stringify(accessibility.violations, null, 2),
  ).toEqual([]);
});
