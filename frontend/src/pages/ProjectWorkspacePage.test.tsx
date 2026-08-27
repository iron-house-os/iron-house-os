import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  AwardedProjectWorkspace,
  Project,
  ProjectCloseoutChecklist,
  ProjectDashboard,
  ProjectLaunchDashboard,
  ProjectStartChecklist,
} from "../api/projects";
import { ProjectInvoicePackageReadiness } from "../api/finance";
import { ProjectWorkspacePage } from "./ProjectWorkspacePage";

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { role: "admin" } }),
}));

const project: Project = {
  id: "11111111-1111-4111-8111-111111111111",
  name: "King George Utility Upgrade",
  client_owner: "City of Surrey",
  municipality: "Surrey",
  project_number: "IHO-1001",
  tender_number: "T-2026-01",
  tender_source: "Owner portal",
  tender_closing_date: "2026-07-30",
  bid_due_date: "2026-07-28",
  estimated_construction_start: "2026-08-15",
  estimated_construction_finish: "2026-12-01",
  project_address: "King George Blvd",
  latitude: 49.1913,
  longitude: -122.849,
  contract_value: null,
  status: "tendering",
  notes: "Tender package in progress.",
  metadata: {},
  supplier_ids: [],
  created_at: "2026-07-04T12:00:00Z",
  updated_at: "2026-07-04T12:00:00Z",
};

const dashboard: ProjectDashboard = {
  project_id: project.id,
  rfq_count: 2,
  supplier_count: 12,
  document_count: 7,
  drawing_count: 5,
  bid_status: "draft",
  readiness_percentage: 80,
};

const awardedProject: Project = {
  ...project,
  name: "Awarded Culvert Replacement",
  project_number: "IH-2026-014",
  status: "awarded",
  workspace_root: "IH-2026-014_AwardedCulvertReplacement",
  workspace_provisioned_at: "2026-08-21T08:30:00Z",
};

const awardedWorkspace: AwardedProjectWorkspace = {
  project_id: awardedProject.id,
  job_number: "IH-2026-014",
  root_folder: "IH-2026-014_AwardedCulvertReplacement",
  entries: [
    { path: "IH-2026-014_AwardedCulvertReplacement/00_Admin", kind: "folder", description: "Administration" },
    { path: "IH-2026-014_AwardedCulvertReplacement/13_Award_Handoff", kind: "folder", description: "Award handoff" },
    { path: "IH-2026-014_AwardedCulvertReplacement/PROJECT_INDEX.md", kind: "file", description: "Index" },
  ],
  project_index: "# Project Index",
  provisioned_at: "2026-08-21T08:30:00Z",
};

const startChecklistDefinitions = [
  ["award_contract", "Contract", "Award notice or executed contract and the client scope record are saved."],
  ["scope_review", "Contract", "Scope, exclusions, allowances, and alternates are reviewed."],
  ["current_documents", "Documents", "Current drawings, specifications, and addenda are confirmed."],
  ["contacts_authority", "Administration", "Project contacts, authority limits, and communication path are confirmed."],
  ["budget_cost_codes", "Cost control", "Baseline budget and project cost codes are established."],
  ["schedule_milestones", "Schedule", "Baseline schedule, milestones, and notice periods are established."],
  ["procurement_plan", "Procurement", "Subcontractor, material, equipment, and procurement plans are established."],
  ["permits_insurance_bonding", "Administration", "Permit, insurance, and bonding requirements are assigned."],
  ["safety_mobilization", "Safety", "Project-specific safety and mobilization requirements are assigned for verification."],
  ["quality_testing_asbuilts", "Quality", "Quality, inspection, testing, and as-built requirements are assigned."],
] as const;

const awardedStartChecklist: ProjectStartChecklist = {
  project_id: awardedProject.id,
  status: "not_ready",
  completed_count: 0,
  total_count: startChecklistDefinitions.length,
  items: startChecklistDefinitions.map(([code, category, label], index) => ({
    code,
    category,
    label,
    sort_order: index + 1,
    completed: false,
    changed_by: null,
    changed_at: null,
  })),
};

const closeoutChecklistDefinitions = [
  ["deficiencies", "Quality", "Deficiencies are closed or carried forward with an owner, due date, and documented basis."],
  ["testing_inspections", "Quality", "Required testing and inspection records are complete and saved to the project record."],
  ["permit_authority_finals", "Administration", "Permit, municipal, utility, or other authority final records are saved when applicable."],
  ["asbuilts_redlines", "Documents", "As-builts, redlines, and final drawing revisions are complete and indexed."],
  ["turnover_warranty", "Turnover", "O&M information, warranties, training, and spare-material obligations are complete or recorded as not applicable."],
  ["demobilization", "Delivery", "Demobilization, cleanup, environmental controls, and remaining site obligations are complete."],
  ["changes_commitments", "Cost control", "Final changes, purchase orders, subcontract commitments, and unresolved exposure are reconciled."],
  ["billing_holdback", "Finance", "Final billing package and holdback status are recorded without inferring issue, payment, or release."],
  ["acceptance_evidence", "Contract", "Client or consultant acceptance, substantial completion, or other contract completion evidence is saved when applicable."],
  ["turnover_index", "Documents", "The closeout package is indexed in the project record with remaining actions clearly assigned."],
] as const;

function closeoutChecklist(projectId = awardedProject.id): ProjectCloseoutChecklist {
  const items = closeoutChecklistDefinitions.map(([code, category, label], index) => ({
    code,
    category,
    label,
    sort_order: index + 1,
    completed: false,
    evidence: null,
    changed_by: null,
    changed_at: null,
  }));
  return {
    project_id: projectId,
    status: "not_ready",
    completed_count: 0,
    total_count: items.length,
    next_incomplete_control: items[0],
    items,
  };
}

function readyCloseoutChecklist(projectId = awardedProject.id): ProjectCloseoutChecklist {
  const checklist = closeoutChecklist(projectId);
  const items = checklist.items.map((item) => ({
    ...item,
    completed: true,
    evidence: `Verified evidence for ${item.code}`,
    changed_by: "test-admin@ironhousecontracting.com",
    changed_at: "2026-08-27T15:00:00Z",
  }));
  return {
    ...checklist,
    status: "ready",
    completed_count: items.length,
    next_incomplete_control: null,
    items,
  };
}

const awardedLaunchDashboard: ProjectLaunchDashboard = {
  project_id: awardedProject.id,
  job_number: "IH-2026-014",
  mobilization_status: "not_ready",
  checklist_completed_count: 0,
  checklist_total_count: 10,
  next_incomplete_control: {
    code: "award_contract",
    category: "Contract",
    label: "Award notice or executed contract and the client scope record are saved.",
  },
  estimate_workspace_count: 1,
  priced_estimate_available: true,
  baseline_budget_total: 125000,
  budget_entry_count: 4,
  po_request_count: 3,
  pending_po_request_count: 2,
  safety_record_counts: {
    safety_permit: 1,
    emergency_action_card: 1,
    daily_hazard_assessment: 2,
    toolbox_talk: 1,
    corrective_action: 0,
  },
  document_count: 7,
  award_baseline_source: "Q-2026-001",
  award_pricing_subtotal: 125000,
  award_cost_budget_status: "needs_cost_allocation",
  uncoded_award_line_count: 4,
  procurement_requirement_count: 3,
  procurement_plan_status: "draft",
};

let releaseChecklistUpdate: (() => void) | null = null;

afterEach(() => {
  releaseChecklistUpdate = null;
  vi.restoreAllMocks();
});

describe("ProjectWorkspacePage", () => {
  it("renders the project list with project summary columns", async () => {
    mockProjectApi();

    renderWorkspace("/projects");

    expect(await screen.findByText(project.name)).toBeInTheDocument();
    const management = screen.getByRole("heading", { name: "Project Filters" }).closest(".space-y-6");
    expect(management).not.toBeNull();
    expect(management).not.toHaveClass("[@media(pointer:coarse)]:!order-last");
    expect(management?.parentElement).not.toHaveClass("[@media(pointer:coarse)]:!grid-cols-1");
    expect(screen.getByRole("columnheader", { name: "Ready" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Docs" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Job #" })).toBeInTheDocument();
    expect(screen.getByText("IHO-1001")).toBeInTheDocument();
    expect(await screen.findByText("80%")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
  });

  it("filters only exact release-smoke records with matching SMOKE job numbers", async () => {
    const smokeProject: Project = {
      ...project,
      id: "33333333-3333-4333-8333-333333333333",
      name: "Release smoke 20260823-100046",
      project_number: "SMOKE-20260823-100046",
    };
    const legitimateSmokeProject: Project = {
      ...project,
      id: "44444444-4444-4444-8444-444444444444",
      name: "Smoke Test Pump Station Upgrade",
      project_number: "IH2026002",
    };
    const mismatchedReleaseSmoke: Project = {
      ...project,
      id: "55555555-5555-4555-8555-555555555555",
      name: "Release smoke 20260823-131404",
      project_number: "SMOKE-20260823-131405",
    };
    mockProjectApiWithProjects([project, smokeProject, legitimateSmokeProject, mismatchedReleaseSmoke]);
    const user = userEvent.setup();
    renderWorkspace("/projects");

    expect(await screen.findByText(project.name)).toBeInTheDocument();
    expect(screen.getByText(smokeProject.name)).toBeInTheDocument();
    expect(screen.getByText(legitimateSmokeProject.name)).toBeInTheDocument();
    expect(screen.getByText(mismatchedReleaseSmoke.name)).toBeInTheDocument();

    await user.type(screen.getByRole("searchbox", { name: "Search projects" }), "100046");
    expect(screen.queryByText(project.name)).not.toBeInTheDocument();
    expect(screen.getByText(smokeProject.name)).toBeInTheDocument();

    await user.clear(screen.getByRole("searchbox", { name: "Search projects" }));
    await user.click(screen.getByRole("checkbox", { name: "Release smoke projects only" }));
    expect(screen.queryByText(project.name)).not.toBeInTheDocument();
    expect(screen.getByText(smokeProject.name)).toBeInTheDocument();
    expect(screen.queryByText(legitimateSmokeProject.name)).not.toBeInTheDocument();
    expect(screen.queryByText(mismatchedReleaseSmoke.name)).not.toBeInTheDocument();
  });

  it("moves only the filtered release smoke projects to recoverable trash after confirmation", async () => {
    const smokeProjects: Project[] = [
      { ...project, id: "33333333-3333-4333-8333-333333333333", name: "Release smoke 20260823-100046", project_number: "SMOKE-20260823-100046" },
      { ...project, id: "44444444-4444-4444-8444-444444444444", name: "Release smoke 20260823-131404", project_number: "SMOKE-20260823-131404" },
    ];
    const fetchMock = mockProjectApiWithProjects([project, ...smokeProjects]);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    renderWorkspace("/projects");

    await screen.findByText(project.name);
    await user.click(screen.getByRole("checkbox", { name: "Release smoke projects only" }));
    await user.click(screen.getByRole("button", { name: "Move 2 release smoke projects to Trash" }));

    await screen.findByText("2 release smoke projects moved to Trash. They can be restored by an administrator.");
    const deletes = fetchMock.mock.calls.filter(([, options]) => options?.method === "DELETE");
    expect(deletes).toHaveLength(2);
    expect(deletes.map(([, options]) => JSON.parse(String(options?.body)).confirmation_name)).toEqual(
      smokeProjects.map((item) => item.name),
    );
    expect(screen.queryByText(project.name)).not.toBeInTheDocument();
  });

  it("re-reads the active release-smoke set before confirmation so retries skip already-trashed records", async () => {
    const staleSmokeProject: Project = {
      ...project,
      id: "33333333-3333-4333-8333-333333333333",
      name: "Release smoke 20260823-100046",
      project_number: "SMOKE-20260823-100046",
    };
    const currentSmokeProject: Project = {
      ...project,
      id: "44444444-4444-4444-8444-444444444444",
      name: "Release smoke 20260823-131404",
      project_number: "SMOKE-20260823-131404",
    };
    const fetchMock = mockProjectApiWithProjects([project, staleSmokeProject, currentSmokeProject], {
      activeProjectsBeforeConfirmation: [project, currentSmokeProject],
    });
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    renderWorkspace("/projects");

    await screen.findByText(project.name);
    await user.click(screen.getByRole("checkbox", { name: "Release smoke projects only" }));
    expect(screen.getByRole("button", { name: "Move 2 release smoke projects to Trash" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Move 2 release smoke projects to Trash" }));

    await screen.findByText("1 release smoke project moved to Trash. They can be restored by an administrator.");
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining("Move 1 filtered release smoke project"));
    const deletes = fetchMock.mock.calls.filter(([, options]) => options?.method === "DELETE");
    expect(deletes).toHaveLength(1);
    expect(JSON.parse(String(deletes[0][1]?.body)).confirmation_name).toBe(currentSmokeProject.name);
  });

  it("preserves partial progress and the exact failing record after a cleanup request fails", async () => {
    const smokeProjects: Project[] = [
      { ...project, id: "33333333-3333-4333-8333-333333333333", name: "Release smoke 20260823-100046", project_number: "SMOKE-20260823-100046" },
      { ...project, id: "44444444-4444-4444-8444-444444444444", name: "Release smoke 20260823-131404", project_number: "SMOKE-20260823-131404" },
      { ...project, id: "55555555-5555-4555-8555-555555555555", name: "Release smoke 20260823-140000", project_number: "SMOKE-20260823-140000" },
    ];
    const fetchMock = mockProjectApiWithProjects([project, ...smokeProjects], { failDeleteAt: 2 });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    renderWorkspace("/projects");

    await screen.findByText(project.name);
    await user.click(screen.getByRole("checkbox", { name: "Release smoke projects only" }));
    await user.click(screen.getByRole("button", { name: "Move 3 release smoke projects to Trash" }));

    expect(
      await screen.findByText(
        "1 release smoke project moved to Trash before cleanup stopped at Release smoke 20260823-131404 (SMOKE-20260823-131404). Cleanup failed",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Move 2 release smoke projects to Trash" })).toBeInTheDocument();
    const deletes = fetchMock.mock.calls.filter(([, options]) => options?.method === "DELETE");
    expect(deletes).toHaveLength(2);
  });

  it("creates an awarded project and delegates job-number generation to IHOS", async () => {
    const fetchMock = mockProjectApi();
    const user = userEvent.setup();
    renderWorkspace("/projects");
    await screen.findByText(project.name);

    await user.type(screen.getByLabelText("Project name"), "Awarded Culvert Replacement");
    await user.selectOptions(screen.getByLabelText("Project stage"), "awarded");

    expect(screen.getByRole("status")).toHaveTextContent("generate the next unique job number");
    await user.click(screen.getByRole("button", { name: "Create awarded job" }));

    await waitFor(() => {
      const createCall = fetchMock.mock.calls.find(([, options]) => options?.method === "POST");
      expect(createCall).toBeDefined();
      expect(JSON.parse(String(createCall?.[1]?.body))).toMatchObject({
        name: "Awarded Culvert Replacement",
        status: "awarded",
      });
      expect(JSON.parse(String(createCall?.[1]?.body))).not.toHaveProperty("project_number");
    });
  });

  it("loads project detail from the route", async () => {
    const fetchMock = mockProjectApi();

    renderWorkspace(`/projects/${project.id}`);

    expect(await screen.findByRole("heading", { name: project.name })).toBeInTheDocument();
    const management = screen.getByRole("heading", { name: "Project Filters" }).closest(".space-y-6");
    expect(management).toHaveClass("order-last", "xl:order-none", "[@media(pointer:coarse)]:!order-last");
    expect(management?.parentElement).toHaveClass("[@media(pointer:coarse)]:!grid-cols-1");
    expect(screen.getByText("City of Surrey - Surrey")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Archive" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Awarded project workspace" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Job launch dashboard" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Awarded job start checklist" })).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => url.toString().includes("/start-checklist"))).toBe(false);
    expect(fetchMock.mock.calls.some(([url]) => url.toString().includes("/launch-dashboard"))).toBe(false);
  });

  it("keeps the awarded project selected when optional launch controls fail", async () => {
    const fetchMock = mockProjectApi(awardedProject, awardedWorkspace, awardedStartChecklist);
    const originalImplementation = fetchMock.getMockImplementation();
    fetchMock.mockImplementation(async (input: RequestInfo | URL, options?: RequestInit) => {
      if (input.toString().endsWith(`/projects/${awardedProject.id}/launch-dashboard`)) {
        return jsonResponse({ detail: "Launch dashboard unavailable" }, 500);
      }
      if (!originalImplementation) throw new Error("Project API mock is unavailable");
      return originalImplementation(input, options);
    });

    renderWorkspace(`/projects/${awardedProject.id}`);

    expect(await screen.findByRole("heading", { name: awardedProject.name })).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`${awardedProject.name} is selected, but its launch dashboard could not be loaded`, "i"))).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Awarded project workspace" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Awarded job start checklist" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Job launch dashboard" })).not.toBeInTheDocument();
  });

  it("shows the stable prepared workspace for an awarded job", async () => {
    mockProjectApi(awardedProject, awardedWorkspace);

    renderWorkspace(`/projects/${awardedProject.id}`);

    const workspace = await screen.findByRole("region", { name: "Awarded project workspace" });
    expect(workspace).toHaveTextContent("Awarded job workspace prepared");
    expect(workspace).toHaveTextContent("IH-2026-014_AwardedCulvertReplacement");
    expect(within(workspace).getByText("00_Admin")).toBeInTheDocument();
    expect(within(workspace).getByText("13_Award_Handoff")).toBeInTheDocument();
  });

  it("shows awarded-job launch indicators with project-scoped handoff links", async () => {
    mockProjectApi(awardedProject, awardedWorkspace, awardedStartChecklist, false, awardedLaunchDashboard);

    renderWorkspace(`/projects/${awardedProject.id}`);

    const launch = await screen.findByRole("region", { name: "Job launch dashboard" });
    expect(launch).toHaveTextContent("Mobilization controls not ready");
    expect(launch).toHaveTextContent("0 of 10");
    expect(launch).toHaveTextContent("Available");
    expect(launch).toHaveTextContent("$125,000");
    expect(launch).toHaveTextContent("3");
    expect(launch).toHaveTextContent("5");
    expect(launch).toHaveTextContent("Only the project-start checklist determines");

    for (const name of ["Estimate", "Budget", "Purchase orders", "Safety", "Documents"]) {
      const link = within(launch).getByRole("link", { name: new RegExp(name) });
      expect(link).toHaveAttribute("href", expect.stringContaining(`projectId=${awardedProject.id}`));
      expect(link).toHaveAttribute("href", expect.stringContaining("projectName=Awarded+Culvert+Replacement"));
    }
  });

  it("updates awarded-job readiness by selecting a pre-populated checklist item", async () => {
    const fetchMock = mockProjectApi(awardedProject, awardedWorkspace, awardedStartChecklist);
    const user = userEvent.setup();
    renderWorkspace(`/projects/${awardedProject.id}`);

    const checklist = await screen.findByRole("region", { name: "Awarded job start checklist" });
    expect(checklist).toHaveTextContent("Not ready");
    expect(checklist).toHaveTextContent("0 of 10");
    expect(within(checklist).getAllByRole("checkbox")).toHaveLength(10);

    await user.click(within(checklist).getByRole("checkbox", { name: /Award notice or executed contract/ }));

    await waitFor(() => {
      const updateCall = fetchMock.mock.calls.find(
        ([url, options]) => url.toString().endsWith("/start-checklist/award_contract") && options?.method === "PATCH",
      );
      expect(updateCall).toBeDefined();
      expect(JSON.parse(String(updateCall?.[1]?.body))).toEqual({ completed: true });
      expect(checklist).toHaveTextContent("Not ready");
      expect(checklist).toHaveTextContent("1 of 10");
      expect(checklist).toHaveTextContent("Recorded by test-admin@ironhousecontracting.com");
    });

    for (const item of awardedStartChecklist.items.slice(1)) {
      await user.click(within(checklist).getAllByRole("checkbox")[item.sort_order - 1]);
      await waitFor(() => {
        expect(checklist).toHaveTextContent(`${item.sort_order} of 10`);
      });
    }

    expect(checklist).toHaveTextContent("Ready");
    expect(
      within(checklist)
        .getAllByRole("checkbox")
        .every((checkbox) => (checkbox as HTMLInputElement).checked),
    ).toBe(true);
  });

  it("serializes checklist updates so an older response cannot replace newer state", async () => {
    mockProjectApi(awardedProject, awardedWorkspace, awardedStartChecklist, true);
    const user = userEvent.setup();
    renderWorkspace(`/projects/${awardedProject.id}`);

    const checklist = await screen.findByRole("region", { name: "Awarded job start checklist" });
    const checkboxes = within(checklist).getAllByRole("checkbox");
    await user.click(checkboxes[0]);

    await waitFor(() => {
      expect(checkboxes.every((checkbox) => (checkbox as HTMLInputElement).disabled)).toBe(true);
      expect(releaseChecklistUpdate).not.toBeNull();
    });
    releaseChecklistUpdate?.();

    await waitFor(() => {
      expect(
        within(checklist)
          .getAllByRole("checkbox")
          .every((checkbox) => !(checkbox as HTMLInputElement).disabled),
      ).toBe(true);
      expect(checklist).toHaveTextContent("1 of 10");
    });
  });

  it("requires and records evidence for project closeout controls", async () => {
    const fetchMock = mockProjectApi(
      awardedProject,
      awardedWorkspace,
      awardedStartChecklist,
      false,
      awardedLaunchDashboard,
      closeoutChecklist(),
    );
    const user = userEvent.setup();
    renderWorkspace(`/projects/${awardedProject.id}`);

    const checklist = await screen.findByRole("region", { name: "Project closeout checklist" });
    expect(checklist).toHaveTextContent("Not ready");
    expect(checklist).toHaveTextContent("0 of 10");
    const evidence = within(checklist).getByRole("textbox", { name: /Evidence for Deficiencies are closed/ });
    const confirm = within(checklist).getAllByRole("button", { name: "Confirm complete" })[0];
    expect(confirm).toBeDisabled();

    await user.type(evidence, "Deficiency log CL-001, reviewed 2026-08-27");
    expect(confirm).toBeEnabled();
    await user.click(confirm);

    await waitFor(() => {
      const updateCall = fetchMock.mock.calls.find(
        ([url, options]) => url.toString().endsWith("/closeout-checklist/deficiencies") && options?.method === "PATCH",
      );
      expect(updateCall).toBeDefined();
      expect(JSON.parse(String(updateCall?.[1]?.body))).toEqual({
        completed: true,
        evidence: "Deficiency log CL-001, reviewed 2026-08-27",
      });
      expect(checklist).toHaveTextContent("1 of 10");
      expect(checklist).toHaveTextContent("Recorded by test-admin@ironhousecontracting.com");
    });
  });

  it("lets management explicitly initialize closeout controls for a legacy job without a workspace manifest", async () => {
    const legacyConstructionProject: Project = {
      ...awardedProject,
      status: "construction",
      workspace_root: null,
      workspace_provisioned_at: null,
    };
    const fetchMock = mockProjectApi(legacyConstructionProject);
    const user = userEvent.setup();
    renderWorkspace(`/projects/${legacyConstructionProject.id}`);

    const initialization = await screen.findByRole("region", { name: "Project closeout controls" });
    await user.click(within(initialization).getByRole("button", { name: "Initialize closeout controls" }));

    expect(await screen.findByRole("region", { name: "Project closeout checklist" })).toHaveTextContent("0 of 10");
    expect(fetchMock.mock.calls.some(
      ([url, options]) => url.toString().endsWith(`/projects/${legacyConstructionProject.id}/closeout-checklist`) && options?.method === "POST",
    )).toBe(true);
    expect(fetchMock.mock.calls.some(([url]) => url.toString().endsWith("/workspace"))).toBe(false);
  });

  it("generates one traceable draft package from an exact completed-work source group", async () => {
    const completedProject: Project = {
      ...awardedProject,
      status: "completed",
      client_owner: "Verified Customer Reference",
      project_address: "100 Verified Site Road",
    };
    const sourceGroup = {
      source_import_key: "verified-source-2026-08-27",
      source_invoice_number: "SOURCE-100",
      source_drive_file_id: "verified-drive-file-id",
      source_invoice_date: "2026-08-21",
      line_count: 1,
      subtotal: "550.00",
      ready: true,
      blockers: [],
      lines: [{
        id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        work_date: "2026-08-20",
        source_line_key: "line-01",
        source_invoice_number: "SOURCE-100",
        description: "Verified excavation work",
        quantity: "2.5",
        unit: "hour",
        billable_rate: "220.00",
        billable_amount: "550.00",
      }],
      existing_invoice_id: null,
      existing_invoice_number: null,
      existing_invoice_status: null,
    };
    let invoiceReadiness: ProjectInvoicePackageReadiness = {
      project_id: completedProject.id,
      project_number: completedProject.project_number,
      project_name: completedProject.name,
      project_status: "completed",
      site_address: completedProject.project_address,
      customer_reference: completedProject.client_owner,
      closeout_status: "ready",
      ready: true,
      blockers: [],
      groups: [sourceGroup],
    };
    const fetchMock = mockProjectApi(
      completedProject,
      awardedWorkspace,
      awardedStartChecklist,
      false,
      awardedLaunchDashboard,
      readyCloseoutChecklist(completedProject.id),
    );
    const originalImplementation = fetchMock.getMockImplementation();
    fetchMock.mockImplementation(async (input: RequestInfo | URL, options?: RequestInit) => {
      const url = input.toString();
      if (url.endsWith(`/finance/projects/${completedProject.id}/invoice-package-readiness`)) {
        return jsonResponse(invoiceReadiness);
      }
      if (url.endsWith(`/finance/projects/${completedProject.id}/invoice-package`) && options?.method === "POST") {
        invoiceReadiness = {
          ...invoiceReadiness,
          groups: [{
            ...sourceGroup,
            existing_invoice_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            existing_invoice_number: "IH2026901INV1",
            existing_invoice_status: "draft",
          }],
        };
        return jsonResponse({
          created: true,
          idempotent: false,
          generated_at: "2026-08-27T16:00:00Z",
          invoice: {
            id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            invoice_number: "IH2026901INV1",
            project_id: completedProject.id,
            project_name: completedProject.name,
            site_address: completedProject.project_address,
            customer_name: "Verified Customer Legal Name",
            customer_address: "200 Verified Billing Avenue",
            customer_phone: null,
            invoice_date: "2026-08-27",
            due_date: "2026-09-26",
            terms: "Net 30",
            status: "draft",
            line_items: [{ description: "Verified excavation work", quantity: "2.5", unit: "hour", unit_price: "220.00", amount: "550.00" }],
            subtotal: "550.00",
            gst_rate: "5.00",
            gst: "27.50",
            total: "577.50",
            development_seed_key: null,
          },
        });
      }
      if (!originalImplementation) throw new Error("Project API mock is unavailable");
      return originalImplementation(input, options);
    });
    const user = userEvent.setup();
    renderWorkspace(`/projects/${completedProject.id}`);

    const packageCard = await screen.findByRole("region", { name: "Draft invoice package" });
    expect(packageCard).toHaveTextContent("Verified excavation work");
    expect(within(packageCard).getByLabelText("Customer legal / billing name")).toHaveValue("Verified Customer Reference");
    await user.clear(within(packageCard).getByLabelText("Customer legal / billing name"));
    await user.type(within(packageCard).getByLabelText("Customer legal / billing name"), "Verified Customer Legal Name");
    await user.type(within(packageCard).getByLabelText("Invoice number"), "IH2026901INV1");
    await user.type(within(packageCard).getByLabelText("Customer billing address"), "200 Verified Billing Avenue");
    await user.click(within(packageCard).getByRole("button", { name: "Generate traceable draft" }));

    await waitFor(() => {
      const createCall = fetchMock.mock.calls.find(
        ([url, options]) => url.toString().endsWith(`/finance/projects/${completedProject.id}/invoice-package`) && options?.method === "POST",
      );
      expect(createCall).toBeDefined();
      const payload = JSON.parse(String(createCall?.[1]?.body));
      expect(payload).toMatchObject({
        source_import_key: "verified-source-2026-08-27",
        invoice_number: "IH2026901INV1",
        customer_name: "Verified Customer Legal Name",
        customer_address: "200 Verified Billing Avenue",
        terms: "Net 30",
        gst_rate: "5.00",
      });
      expect(payload).not.toHaveProperty("line_items");
      expect(payload).not.toHaveProperty("project_name");
    });
    expect(await within(packageCard).findByRole("link", { name: "Open draft PDF" })).toHaveAttribute(
      "href",
      expect.stringContaining("/finance/customer-invoices/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb/pdf"),
    );
    expect(packageCard).toHaveTextContent("Status: Draft");
    expect(packageCard).toHaveTextContent("does not approve, issue, send, export, mark paid, release holdback");
  });

  it("renders dashboard widgets for project readiness", async () => {
    mockProjectApi();

    renderWorkspace(`/projects/${project.id}`);

    const widgets = await screen.findByText("RFQ readiness");
    expect(widgets).toBeInTheDocument();
    expect(screen.getAllByText("Supplier coverage").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Drawings").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Bid status").length).toBeGreaterThan(0);

    const detailPanel = screen.getByText("Project Workspace").closest("section");
    expect(detailPanel).not.toBeNull();
    expect(within(detailPanel as HTMLElement).getAllByText("80%").length).toBeGreaterThan(0);
    expect(screen.getByText("Draft")).toBeInTheDocument();
  });

  it("keeps project context on estimating links", async () => {
    mockProjectApi();

    renderWorkspace(`/projects/${project.id}`);

    await screen.findByRole("heading", { name: project.name });
    const estimatingLinks = screen.getAllByRole("link").filter((link) => link.getAttribute("href")?.startsWith("/estimating?"));
    expect(estimatingLinks.length).toBeGreaterThan(0);
    for (const link of estimatingLinks) {
      expect(link).toHaveAttribute("href", expect.stringContaining(`projectId=${project.id}`));
      expect(link).toHaveAttribute("href", expect.stringContaining("projectName=King+George+Utility+Upgrade"));
    }
  });

  it("routes command-center actions to the correct project tools", async () => {
    mockProjectApi();

    renderWorkspace(`/projects/${project.id}`);
    await screen.findByRole("heading", { name: project.name });

    expect(screen.getByRole("link", { name: /Municipality/ })).toHaveAttribute(
      "href",
      expect.stringContaining(`/municipality-intelligence?projectId=${project.id}`),
    );
    expect(screen.getByRole("link", { name: /Bid Package/ })).toHaveAttribute(
      "href",
      expect.stringContaining(`/bid-package?projectId=${project.id}`),
    );
    expect(screen.getByRole("link", { name: /Schedule/ })).toHaveAttribute(
      "href",
      `/projects/${project.id}`,
    );
  });
});

function renderWorkspace(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/projects" element={<ProjectWorkspacePage />} />
        <Route path="/projects/:projectId" element={<ProjectWorkspacePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

function mockProjectApi(
  currentProject: Project = project,
  workspace?: AwardedProjectWorkspace,
  startChecklist?: ProjectStartChecklist,
  delayChecklistUpdates = false,
  launchDashboard: ProjectLaunchDashboard = awardedLaunchDashboard,
  closeout?: ProjectCloseoutChecklist,
) {
  let currentStartChecklist = startChecklist;
  let currentCloseoutChecklist = closeout;
  const fetchMock = vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
    const url = input.toString();

    if (url.endsWith("/projects") && options?.method === "POST") {
      const payload = JSON.parse(String(options.body));
      return jsonResponse({
        ...currentProject,
        ...payload,
        id: "22222222-2222-4222-8222-222222222222",
        project_number: "IH-2026-001",
      }, 201);
    }

    if (url.endsWith("/projects")) {
      return jsonResponse({ items: [currentProject], total: 1 });
    }

    if (url.endsWith(`/projects/${currentProject.id}/dashboard`)) {
      return jsonResponse(dashboard);
    }

    if (url.endsWith(`/projects/${currentProject.id}/workspace`) && workspace) {
      return jsonResponse(workspace);
    }

    if (url.endsWith(`/projects/${currentProject.id}/start-checklist`) && currentStartChecklist) {
      return jsonResponse(currentStartChecklist);
    }

    if (url.endsWith(`/projects/${currentProject.id}/launch-dashboard`) && workspace) {
      return jsonResponse({
        ...launchDashboard,
        project_id: currentProject.id,
        job_number: currentProject.project_number,
        mobilization_status: currentStartChecklist?.status ?? launchDashboard.mobilization_status,
        checklist_completed_count: currentStartChecklist?.completed_count ?? launchDashboard.checklist_completed_count,
        checklist_total_count: currentStartChecklist?.total_count ?? launchDashboard.checklist_total_count,
        next_incomplete_control: currentStartChecklist
          ? currentStartChecklist.items.find((item) => !item.completed) ?? null
          : launchDashboard.next_incomplete_control,
      });
    }

    const closeoutItemPath = `/projects/${currentProject.id}/closeout-checklist/`;
    if (url.includes(closeoutItemPath) && options?.method === "PATCH" && currentCloseoutChecklist) {
      const payload = JSON.parse(String(options.body));
      const code = decodeURIComponent(url.slice(url.indexOf(closeoutItemPath) + closeoutItemPath.length));
      const items = currentCloseoutChecklist.items.map((item) =>
        item.code === code
          ? {
              ...item,
              completed: payload.completed,
              evidence: payload.completed ? payload.evidence : null,
              changed_by: "test-admin@ironhousecontracting.com",
              changed_at: "2026-08-27T15:00:00Z",
            }
          : item,
      );
      const completedCount = items.filter((item) => item.completed).length;
      currentCloseoutChecklist = {
        ...currentCloseoutChecklist,
        status: completedCount === currentCloseoutChecklist.total_count ? "ready" : "not_ready",
        completed_count: completedCount,
        next_incomplete_control: items.find((item) => !item.completed) ?? null,
        items,
      };
      return jsonResponse(currentCloseoutChecklist);
    }

    if (url.endsWith(`/projects/${currentProject.id}/closeout-checklist`) && options?.method === "POST") {
      currentCloseoutChecklist = closeoutChecklist(currentProject.id);
      return jsonResponse(currentCloseoutChecklist, 201);
    }

    if (url.endsWith(`/projects/${currentProject.id}/closeout-checklist`) && currentCloseoutChecklist) {
      return jsonResponse(currentCloseoutChecklist);
    }

    const checklistItemPath = `/projects/${currentProject.id}/start-checklist/`;
    if (url.includes(checklistItemPath) && options?.method === "PATCH" && currentStartChecklist) {
      if (delayChecklistUpdates) {
        await new Promise<void>((resolve) => {
          releaseChecklistUpdate = resolve;
        });
      }
      const payload = JSON.parse(String(options?.body));
      const code = decodeURIComponent(url.slice(url.indexOf(checklistItemPath) + checklistItemPath.length));
      const items = currentStartChecklist.items.map((item) =>
        item.code === code
          ? {
              ...item,
              completed: payload.completed,
              changed_by: "test-admin@ironhousecontracting.com",
              changed_at: "2026-08-21T10:00:00Z",
            }
          : item,
      );
      const completedCount = items.filter((item) => item.completed).length;
      currentStartChecklist = {
        ...currentStartChecklist,
        status: completedCount === currentStartChecklist.total_count ? "ready" : "not_ready",
        completed_count: completedCount,
        items,
      };
      return jsonResponse(currentStartChecklist);
    }

    if (url.endsWith(`/projects/${currentProject.id}`)) {
      return jsonResponse(currentProject);
    }

    return jsonResponse({ detail: "Not found" }, 404);
  });

  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function mockProjectApiWithProjects(
  initialProjects: Project[],
  mockOptions: { failDeleteAt?: number; activeProjectsBeforeConfirmation?: Project[] } = {},
) {
  let projects = initialProjects;
  let deleteCalls = 0;
  let listCalls = 0;
  const fetchMock = vi.fn(async (input: RequestInfo | URL, requestOptions?: RequestInit) => {
    const url = input.toString();
    if (requestOptions?.method === "DELETE") {
      deleteCalls += 1;
      if (deleteCalls === mockOptions.failDeleteAt) return jsonResponse({ detail: "Cleanup failed" }, 500);
      const deleted = projects.find((item) => url.endsWith(`/projects/${item.id}`));
      if (!deleted) return jsonResponse({ detail: "Not found" }, 404);
      projects = projects.filter((item) => item.id !== deleted.id);
      return jsonResponse({ ...deleted, deleted_at: "2026-08-23T15:00:00Z" });
    }
    if (url.endsWith("/projects")) {
      listCalls += 1;
      if (listCalls === 2 && mockOptions.activeProjectsBeforeConfirmation) {
        projects = mockOptions.activeProjectsBeforeConfirmation;
      }
      return jsonResponse({ items: projects, total: projects.length });
    }
    const dashboardProject = projects.find((item) => url.endsWith(`/projects/${item.id}/dashboard`));
    if (dashboardProject) return jsonResponse({ ...dashboard, project_id: dashboardProject.id });
    throw new Error(`Unhandled request: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}
