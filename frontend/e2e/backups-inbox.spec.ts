import AxeBuilder from "@axe-core/playwright";
import { expect, Page, test } from "@playwright/test";

const user = {
  id: "00000000-0000-0000-0000-000000000154",
  email: "backups-acceptance@ironhousecontracting.com",
  display_name: "Backups Acceptance Manager",
  role: "admin",
  is_active: true,
  password_reset_required: false,
  last_login_at: null,
  created_at: "2026-08-05T00:00:00Z",
  updated_at: "2026-08-05T00:00:00Z",
};

const mediaId = "00000000-0000-0000-0000-000000000155";
const intakeId = "00000000-0000-0000-0000-000000000156";
const image = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
  "base64",
);

function intake() {
  return {
    id: intakeId,
    media_id: mediaId,
    media_hash: "a".repeat(64),
    uploader_id: user.id,
    uploader_email: user.email,
    uploader_role: "administrator",
    upload_timestamp: "2026-08-05T12:00:00Z",
    note: "Fuel receipt",
    project_hint: "Main Street",
    status: "pending",
    detected_type: null,
    confidence: null,
    classification_source: null,
    review_destination: null,
    routing_version: 0,
    destination_type: null,
    destination_record_id: null,
    error: null,
    sensitive_quarantine: false,
    attempt_count: 0,
    last_attempt_at: null,
    processing_started_at: null,
    processed_at: null,
    routed_at: null,
    failed_at: null,
    created_at: "2026-08-05T12:00:00Z",
    updated_at: "2026-08-05T12:00:00Z",
    audit_history: [{ id: "00000000-0000-0000-0000-000000000157", action: "submitted", actor_email: user.email, from_status: null, to_status: "pending", details: {}, created_at: "2026-08-05T12:00:00Z" }],
  };
}

async function mockBackupsApi(page: Page) {
  let items: ReturnType<typeof intake>[] = [];
  await page.route("http://localhost:8000/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/auth/me")) {
      await route.fulfill({ status: 200, json: { authentication: "authenticated", user } });
      return;
    }
    if (path.endsWith("/auth/me/permissions")) {
      await route.fulfill({
        status: 200,
        json: { role: "admin", modules: { backups: ["read", "write"], media: ["read", "write"] } },
      });
      return;
    }
    if (path.endsWith("/media") && request.method() === "POST") {
      expect(request.postData() ?? "").toContain('name="files"');
      await route.fulfill({ status: 201, json: [{ id: mediaId }] });
      return;
    }
    if (path.endsWith("/backups/controller/daily") && request.method() === "POST") {
      items = items.map((item) => ({ ...item, status: "routed", detected_type: "receipt", confidence: 0.94, classification_source: "local_ocr", review_destination: "finance_intake", processed_at: "2026-08-05T12:01:00Z", routed_at: "2026-08-05T12:01:00Z", attempt_count: 1 }));
      await route.fulfill({ status: 200, json: { claimed: 1, routed: 1, needs_review: 0, failed: 0 } });
      return;
    }
    if (path.endsWith(`/backups/${intakeId}/destination`) && request.method() === "PATCH") {
      expect(request.postDataJSON()).toEqual({ destination: "finance_receipts", expected_version: 0 });
      items = items.map((item) => ({ ...item, review_destination: "finance_receipts", routing_version: 1 }));
      await route.fulfill({ status: 200, json: items[0] });
      return;
    }
    if (path.endsWith("/backups") && request.method() === "POST") {
      expect(request.postDataJSON()).toMatchObject({
        media_id: mediaId,
        note: "Fuel receipt",
        project_hint: "Main Street",
      });
      items = [intake()];
      await route.fulfill({ status: 201, json: items[0] });
      return;
    }
    if (path.endsWith("/backups")) {
      await route.fulfill({ status: 200, json: { items, total: items.length } });
      return;
    }
    if (path.endsWith(`/${mediaId}/content`)) {
      await route.fulfill({ status: 200, body: image, contentType: "image/png" });
      return;
    }
    await route.fulfill({ status: 200, json: { items: [], total: 0 } });
  });
}

test("single-photo Backups intake is responsive, private, and accessible", async ({ page }) => {
  await mockBackupsApi(page);
  await page.goto("/backups");

  await expect(page.getByRole("heading", { name: "Backups", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Company queue" })).toBeVisible();
  const photo = page.getByLabel("Photo");
  await expect(photo).toHaveAttribute("accept", "image/*");
  await expect(photo).toHaveAttribute("capture", "environment");
  await expect(photo).not.toHaveAttribute("multiple", "");
  await photo.setInputFiles({ name: "receipt.png", mimeType: "image/png", buffer: image });
  await page.getByLabel("Optional note").fill("Fuel receipt");
  await page.getByLabel("Optional project hint").fill("Main Street");
  await page.getByRole("button", { name: "Store photo in Backups" }).click();

  await expect(page.getByRole("status")).toContainText("Photo stored");
  await expect(page.getByText("Fuel receipt", { exact: true })).toBeVisible();
  await expect(page.getByAltText("Private Backups original")).toBeVisible();
  await expect(page.getByText("1 audit event(s) · 0 controller attempt(s)")).toBeVisible();
  await page.getByRole("button", { name: "Run daily controller" }).click();
  const destination = page.getByLabel(`Review destination for ${intakeId}`);
  await expect(destination).toHaveValue("finance_intake");
  await destination.selectOption("finance_receipts");
  await expect(destination).toHaveValue("finance_receipts");

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
