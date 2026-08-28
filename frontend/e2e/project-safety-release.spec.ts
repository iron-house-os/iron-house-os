import AxeBuilder from "@axe-core/playwright";
import { expect, Page, test } from "@playwright/test";

const projectId = "23400000-0000-4000-8000-000000000001";
const documentId = "23400000-0000-4000-8000-000000000002";
const employeeId = "23400000-0000-4000-8000-000000000003";
const project = {
  id: projectId,
  name: "Controlled Crew Launch",
  client_owner: "Verified Owner",
  municipality: "Surrey",
  project_number: "IH2026234",
  tender_number: null,
  tender_source: null,
  tender_closing_date: null,
  bid_due_date: null,
  estimated_construction_start: null,
  estimated_construction_finish: null,
  project_address: "100 Verified Project Road",
  latitude: null,
  longitude: null,
  contract_value: null,
  status: "awarded",
  notes: null,
  metadata: {},
  workspace_root: "IH2026234_ControlledCrewLaunch",
  workspace_provisioned_at: "2026-08-28T15:00:00Z",
  deleted_at: null,
  supplier_ids: [],
  created_at: "2026-08-28T15:00:00Z",
  updated_at: "2026-08-28T15:00:00Z",
};
const requirementDefinitions = [
  ["project_safety_plan", "Project-specific safety plan"],
  ["emergency_action_card", "Emergency action card"],
  ["field_hazard_assessment", "Field-level hazard assessment"],
  ["toolbox_talk", "Crew toolbox talk"],
  ["safety_permit", "Task permit or safety-control record, if applicable"],
  ["orientation_verification", "Crew orientation and qualification verification"],
] as const;

function safetyControls() {
  return {
    launch: {
      project_id: projectId,
      job_number: project.project_number,
      release_status: "blocked",
      folder_path: `${project.workspace_root}/13_Award_Handoff/Safety`,
      folder_status: "prepared",
      record_requirements: requirementDefinitions.map(([code, label]) => ({
        code,
        label,
        applicability_status: "applicable",
        status: "ready",
        record_id: null,
        evidence_document_ids: [documentId],
        not_applicable_basis: null,
        reviewed_by: "release-gate@ironhousecontracting.com",
        reviewed_at: "2026-08-28T15:30:00Z",
      })),
      portal_access: { status: "not_started", automatic_provisioning: false, assignments: [] },
      initialized_by: "release-gate@ironhousecontracting.com",
      initialized_at: "2026-08-28T15:00:00Z",
      last_reviewed_by: null,
      last_reviewed_at: null,
      last_review_note: null,
      review_history: [],
    },
    evidence_documents: [{ id: documentId, title: "Current controlled safety package", category: "other", status: "current" }],
    record_options: [],
    active_employees: [{ id: employeeId, display_name: "Sam Foreperson", portal_role: "foreman" }],
    posting_blockers: [
      { code: "safety_release", message: "Safety release must be Ready before field production can post." },
      { code: "portal_access", message: "Project portal access and at least one worker assignment must be active before field production can post." },
      { code: "mobilization", message: "The project-start checklist must be complete before field production can post." },
    ],
  };
}

async function mockApi(page: Page) {
  let authenticated = false;
  let controls = safetyControls();
  let savedPayload: Record<string, unknown> | null = null;
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/auth/me")) {
      await route.fulfill(authenticated ? {
        status: 200,
        json: {
          authentication: "authenticated",
          user: {
            id: "23400000-0000-4000-8000-000000000004",
            email: "release-gate@ironhousecontracting.com",
            display_name: "Release Gate Admin",
            role: "admin",
            is_active: true,
            password_reset_required: false,
            last_login_at: null,
            created_at: "2026-08-28T15:00:00Z",
            updated_at: "2026-08-28T15:00:00Z",
          },
        },
      } : { status: 401, json: { detail: "Sign in is required." } });
      return;
    }
    if (path.endsWith("/auth/login") && request.method() === "POST") {
      authenticated = true;
      await route.fulfill({
        status: 200,
        json: {
          authentication: "authenticated",
          user: {
            id: "23400000-0000-4000-8000-000000000004",
            email: "release-gate@ironhousecontracting.com",
            display_name: "Release Gate Admin",
            role: "admin",
            is_active: true,
            password_reset_required: false,
          },
        },
      });
      return;
    }
    if (path.endsWith("/auth/me/permissions")) {
      await route.fulfill({ status: 200, json: { role: "admin", modules: { projects: ["read", "write"] } } });
      return;
    }
    if (path === "/api/v1/projects") {
      await route.fulfill({ status: 200, json: { items: [project], total: 1 } });
      return;
    }
    if (path.endsWith(`/projects/${projectId}/dashboard`)) {
      await route.fulfill({ status: 200, json: { project_id: projectId, rfq_count: 0, supplier_count: 0, document_count: 1, drawing_count: 0, bid_status: "draft", readiness_percentage: 60 } });
      return;
    }
    if (path.endsWith(`/projects/${projectId}/workspace`)) {
      await route.fulfill({ status: 200, json: { project_id: projectId, job_number: project.project_number, root_folder: project.workspace_root, entries: [], project_index: "# Project", provisioned_at: project.workspace_provisioned_at } });
      return;
    }
    if (path.endsWith(`/projects/${projectId}/start-checklist`)) {
      await route.fulfill({ status: 200, json: { project_id: projectId, status: "not_ready", completed_count: 0, total_count: 1, items: [{ code: "safety_mobilization", category: "Safety", label: "Project-specific safety controls are complete.", sort_order: 1, completed: false, changed_by: null, changed_at: null }] } });
      return;
    }
    if (path.endsWith(`/projects/${projectId}/launch-dashboard`)) {
      await route.fulfill({
        status: 200,
        json: {
          project_id: projectId, job_number: project.project_number, mobilization_status: "not_ready",
          checklist_completed_count: 0, checklist_total_count: 1,
          next_incomplete_control: { code: "safety_mobilization", category: "Safety", label: "Project-specific safety controls are complete." },
          estimate_workspace_count: 0, priced_estimate_available: false, baseline_budget_total: 0, budget_entry_count: 0,
          po_request_count: 0, pending_po_request_count: 0, safety_record_counts: {}, safety_release_status: controls.launch.release_status,
          safety_requirement_count: 6, safety_folder_status: "prepared", portal_access_status: controls.launch.portal_access.status,
          portal_assignment_count: controls.launch.portal_access.assignments.length, production_posting_status: "blocked",
          production_blockers: controls.posting_blockers.map((item) => item.code), daily_sheet_count: 0, production_post_count: 0,
          latest_daily_sheet_status: "not_started", field_production_folder_status: "not_initialized", document_count: 1,
          award_baseline_source: null, award_pricing_subtotal: 0, award_cost_budget_status: "not_initialized",
          uncoded_award_line_count: 0, procurement_requirement_count: 0, procurement_plan_status: "not_initialized",
        },
      });
      return;
    }
    if (path.endsWith(`/projects/${projectId}/safety-launch/controls`)) {
      await route.fulfill({ status: 200, json: controls });
      return;
    }
    if (path.endsWith(`/projects/${projectId}/safety-launch`) && request.method() === "PATCH") {
      savedPayload = request.postDataJSON();
      controls = {
        ...controls,
        launch: {
          ...controls.launch,
          release_status: "ready",
          portal_access: {
            status: "active",
            automatic_provisioning: false,
            assignments: [{ employee_id: employeeId, portal_role: "foreman", status: "active" }],
          },
          last_reviewed_by: "release-gate@ironhousecontracting.com",
          last_reviewed_at: "2026-08-28T16:00:00Z",
          last_review_note: "Reviewed current evidence and exact crew assignment.",
        },
        posting_blockers: [{ code: "mobilization", message: "The project-start checklist must be complete before field production can post." }],
      };
      await route.fulfill({ status: 200, json: controls });
      return;
    }
    if (path.endsWith(`/projects/${projectId}`)) {
      await route.fulfill({ status: 200, json: project });
      return;
    }
    if (path.endsWith(`/projects/${projectId}/closeout-checklist`)) {
      await route.fulfill({ status: 404, json: { detail: "Not initialized" } });
      return;
    }
    await route.fulfill({ status: 404, json: { detail: "Not found" } });
  });
  return () => savedPayload;
}

test("management safety and crew release stays explicit, responsive, and accessible", async ({ page }) => {
  const savedPayload = await mockApi(page);
  await page.goto("/");
  await page.getByLabel("Email").fill("release-gate@ironhousecontracting.com");
  await page.getByLabel("Password").fill("Local-release-gate-only");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.goto(`/projects/${projectId}`);

  const release = page.getByRole("region", { name: "Project safety and crew release" });
  await expect(release).toBeVisible();
  await expect(release.getByText("Field posting remains blocked")).toBeVisible();
  const save = release.getByRole("button", { name: "Save controlled release" });
  await expect(save).toBeDisabled();

  await release.getByRole("checkbox", { name: /Sam Foreperson/ }).check();
  await release.getByLabel("Safety release status").selectOption("ready");
  await release.getByLabel("Safety release review note").fill("Reviewed current evidence and exact crew assignment.");
  await expect(save).toBeDisabled();
  await release.getByRole("checkbox", { name: /I confirm every requirement/ }).check();
  await expect(save).toBeEnabled();
  await save.click();

  await expect(page.getByText(/Last reviewed by release-gate@ironhousecontracting.com/)).toBeVisible();
  expect(savedPayload()).toMatchObject({
    release_status: "ready",
    release_confirmation: true,
    portal_access: {
      status: "active",
      assignments: [{ employee_id: employeeId, portal_role: "foreman", status: "active" }],
    },
  });
  const overflow = await page.evaluate(() => ({
    width: document.documentElement.scrollWidth,
    viewport: document.documentElement.clientWidth,
  }));
  expect(overflow.width).toBe(overflow.viewport);
  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(
    accessibility.violations.filter(({ impact }) => impact === "critical" || impact === "serious"),
    JSON.stringify(accessibility.violations, null, 2),
  ).toEqual([]);
});
