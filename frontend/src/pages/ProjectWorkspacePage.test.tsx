import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  AwardedProjectWorkspace,
  Project,
  ProjectDashboard,
  ProjectLaunchDashboard,
  ProjectStartChecklist,
} from "../api/projects";
import { ProjectWorkspacePage } from "./ProjectWorkspacePage";

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
    expect(screen.getByRole("columnheader", { name: "Ready" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Docs" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Job #" })).toBeInTheDocument();
    expect(screen.getByText("IHO-1001")).toBeInTheDocument();
    expect(await screen.findByText("80%")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
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
    expect(screen.getByText("City of Surrey - Surrey")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Archive" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Awarded project workspace" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Job launch dashboard" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Awarded job start checklist" })).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => url.toString().includes("/start-checklist"))).toBe(false);
    expect(fetchMock.mock.calls.some(([url]) => url.toString().includes("/launch-dashboard"))).toBe(false);
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
) {
  let currentStartChecklist = startChecklist;
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

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}
