import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CustomerQuote } from "../api/customerQuotes";
import { Project, ProjectLaunchDashboard } from "../api/projects";
import { MVPWorkflowPage } from "./MVPWorkflowPage";

const draft = {
  id: "draft-246",
  owner_account_id: "owner-1",
  project_id: "project-1",
  workflow_type: "purchase_order_request",
  title: "PO request — Pipe and fittings",
  payload: { purpose: "Pipe and fittings" },
  schema_version: 1,
  revision: 3,
  status: "active",
  last_saved_at: "2026-08-21T06:30:00Z",
  created_at: "2026-08-21T06:00:00Z",
  updated_at: "2026-08-21T06:30:00Z",
};

const draftQuote = customerQuote({
  id: "quote-draft",
  project_id: "quote-project-draft",
  project_name: "Driveway culvert",
  customer_name: "Morgan Lee",
  quote_number: "Q-2026-001",
  status: "draft",
});
const sentQuote = customerQuote({
  id: "quote-sent",
  project_id: "quote-project-sent",
  project_name: "Storm repair",
  customer_name: "Avery Chen",
  quote_number: "Q-2026-002",
  status: "sent",
});
const launchJob = project({
  id: "project-launch",
  name: "Awarded launch job",
  status: "awarded",
  project_number: "IH-2026-021",
  workspace_root: "IH-2026-021_AwardedLaunchJob",
});
const readyJob = project({
  id: "project-ready",
  name: "Ready job",
  status: "awarded",
  project_number: "IH-2026-022",
  workspace_root: "IH-2026-022_ReadyJob",
});
const constructionJob = project({
  id: "project-construction",
  name: "Active construction job",
  status: "construction",
  project_number: "IH-2026-020",
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("MVPWorkflowPage", () => {
  it("keeps durable unfinished work with direct resume and audited discard controls", async () => {
    const fetchMock = mockApi({ drafts: [draft] });
    const user = userEvent.setup();

    renderWorkflow();

    expect(await screen.findByText("PO request — Pipe and fittings")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Continue" })).toHaveAttribute(
      "href",
      "/request-po?draftId=draft-246&projectId=project-1",
    );

    await user.click(screen.getByRole("button", { name: "Discard" }));
    await waitFor(() => expect(screen.queryByText("PO request — Pipe and fittings")).not.toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/workflow-drafts/draft-246/cancel"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("derives one next action from quote through award, launch, and delivery", async () => {
    mockApi({
      quotes: [draftQuote, sentQuote],
      projects: [
        project({ id: draftQuote.project_id, name: draftQuote.project_name }),
        project({ id: sentQuote.project_id, name: sentQuote.project_name }),
        launchJob,
        readyJob,
        constructionJob,
      ],
      launches: {
        [launchJob.id]: launchDashboard(launchJob, "not_ready"),
        [readyJob.id]: launchDashboard(readyJob, "ready"),
      },
    });

    renderWorkflow();

    const queue = await screen.findByLabelText("Active quote-to-job work queue");
    const stages = screen.getByLabelText("Quote-to-job stages");
    for (const label of ["Capture quote", "Record decision", "Award + job number", "Launch controls", "Deliver + closeout"]) {
      expect(stages).toHaveTextContent(label);
    }

    const draftCard = within(queue).getByText("Morgan Lee — Driveway culvert").closest("article");
    expect(draftCard).not.toBeNull();
    expect(within(draftCard as HTMLElement).getByRole("link", { name: "Finish quote" })).toHaveAttribute(
      "href",
      "/customer-quotes?quoteId=quote-draft&action=edit",
    );

    const sentCard = within(queue).getByText("Avery Chen — Storm repair").closest("article");
    expect(within(sentCard as HTMLElement).getByRole("link", { name: "Record customer decision" })).toHaveAttribute(
      "href",
      "/customer-quotes?quoteId=quote-sent&action=decision",
    );

    const launchCard = within(queue).getByText("Awarded launch job").closest("article");
    await waitFor(() => expect(launchCard).toHaveTextContent("3 of 10 start controls"));
    expect(within(launchCard as HTMLElement).getByRole("link", { name: "Complete launch controls" })).toHaveAttribute(
      "href",
      `/projects/${launchJob.id}`,
    );

    const readyCard = within(queue).getByText("Ready job").closest("article");
    expect(readyCard).toHaveTextContent("All 10 start controls are confirmed");
    expect(within(readyCard as HTMLElement).getByRole("link", { name: "Begin project operations" })).toHaveAttribute(
      "href",
      expect.stringContaining(`/project-operations?projectId=${readyJob.id}`),
    );
    expect(within(readyCard as HTMLElement).getByRole("link", { name: "PO requests" })).toHaveAttribute(
      "href",
      expect.stringContaining(`/request-po?projectId=${readyJob.id}`),
    );

    const constructionCard = within(queue).getByText("Active construction job").closest("article");
    expect(within(constructionCard as HTMLElement).getByRole("link", { name: "Continue project operations" })).toHaveAttribute(
      "href",
      expect.stringContaining(`projectId=${constructionJob.id}`),
    );
    expect(within(constructionCard as HTMLElement).getByRole("link", { name: "PO requests" })).toHaveAttribute(
      "href",
      expect.stringContaining(`/request-po?projectId=${constructionJob.id}`),
    );
    expect(within(constructionCard as HTMLElement).getByRole("link", { name: "Documents" })).toHaveAttribute(
      "href",
      expect.stringContaining(`/documents?projectId=${constructionJob.id}`),
    );
    expect(within(constructionCard as HTMLElement).getByRole("link", { name: "Closeout controls" })).toHaveAttribute(
      "href",
      `/projects/${constructionJob.id}`,
    );
    expect(within(queue).getAllByRole("article")).toHaveLength(5);
  });

  it("shows awarded and construction records even if a stale active quote references them", async () => {
    mockApi({
      quotes: [customerQuote({ project_id: constructionJob.id, status: "draft" })],
      projects: [constructionJob],
    });

    renderWorkflow();

    const queue = await screen.findByLabelText("Active quote-to-job work queue");
    expect(within(queue).getByText("Quote draft")).toBeInTheDocument();
    expect(within(queue).getByText("Active delivery")).toBeInTheDocument();
    expect(within(queue).getAllByRole("article")).toHaveLength(2);
  });

  it("renders awarded jobs before bounded launch summaries finish and includes legacy jobs", async () => {
    let maxConcurrentLaunches = 0;
    let releaseLaunches = () => {};
    const launchGate = new Promise<void>((resolve) => { releaseLaunches = resolve; });
    const jobs = Array.from({ length: 5 }, (_, index) => project({
      id: `legacy-awarded-${index + 1}`,
      name: `Legacy awarded ${index + 1}`,
      status: "awarded",
      project_number: `IH-2026-${30 + index}`,
      workspace_root: null,
    }));
    const launches = Object.fromEntries(jobs.map((job) => [job.id, launchDashboard(job, "not_ready")]));
    const fetchMock = mockApi({
      projects: jobs,
      launches,
      launchGate,
      onLaunchActivity: (active) => { maxConcurrentLaunches = Math.max(maxConcurrentLaunches, active); },
    });

    renderWorkflow();

    expect(await screen.findByText("Legacy awarded 1")).toBeInTheDocument();
    expect(screen.getByText("5 active")).toBeInTheDocument();
    expect(screen.getAllByText(/launch summary is temporarily unavailable/i)).toHaveLength(5);

    await waitFor(() => expect(
      fetchMock.mock.calls.filter(([input]) => String(input).includes("/launch-dashboard")),
    ).toHaveLength(3));
    expect(maxConcurrentLaunches).toBe(3);
    releaseLaunches();
    await waitFor(() => expect(
      fetchMock.mock.calls.filter(([input]) => String(input).includes("/launch-dashboard")),
    ).toHaveLength(5));
    for (const job of jobs) {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining(`/projects/${job.id}/launch-dashboard`),
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      );
    }
  });

  it("keeps available work usable when one source fails", async () => {
    mockApi({ projects: [constructionJob], failQuotes: true });

    renderWorkflow();

    expect(await screen.findByText("Customer quotes could not be loaded.")).toBeInTheDocument();
    expect(screen.getByText("Available work remains usable below.")).toBeInTheDocument();
    expect(screen.getByText("Active construction job")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Continue project operations" })).toBeInTheDocument();
  });
});

function renderWorkflow() {
  render(<MemoryRouter><MVPWorkflowPage /></MemoryRouter>);
}

function mockApi({
  drafts = [],
  quotes = [],
  projects = [],
  launches = {},
  failQuotes = false,
  launchDelay = 0,
  launchGate,
  onLaunchActivity,
}: {
  drafts?: (typeof draft)[];
  quotes?: CustomerQuote[];
  projects?: Project[];
  launches?: Record<string, ProjectLaunchDashboard>;
  failQuotes?: boolean;
  launchDelay?: number;
  launchGate?: Promise<void>;
  onLaunchActivity?: (active: number) => void;
} = {}) {
  let activeLaunches = 0;
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = input.toString();
    if (url.includes("/workflow-drafts/") && url.endsWith("/cancel") && init?.method === "POST") {
      return response({ ...draft, status: "cancelled", revision: 4 });
    }
    if (url.endsWith("/workflow-drafts")) return response({ items: drafts, total: drafts.length });
    if (url.endsWith("/customer-quotes")) {
      return failQuotes ? response({ detail: "Unavailable" }, 503) : response({ items: quotes, total: quotes.length });
    }
    const launchMatch = url.match(/\/projects\/([^/]+)\/launch-dashboard$/);
    if (launchMatch) {
      activeLaunches += 1;
      onLaunchActivity?.(activeLaunches);
      try {
        if (launchGate) await launchGate;
        if (launchDelay) await new Promise((resolve) => window.setTimeout(resolve, launchDelay));
        const launch = launches[launchMatch[1]];
        return launch ? response(launch) : response({ detail: "Unavailable" }, 503);
      } finally {
        activeLaunches -= 1;
        onLaunchActivity?.(activeLaunches);
      }
    }
    if (url.endsWith("/projects")) return response({ items: projects, total: projects.length });
    return response({ detail: "Not found" }, 404);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function response(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function customerQuote(overrides: Partial<CustomerQuote>): CustomerQuote {
  return {
    id: "quote-1",
    project_id: "project-1",
    source_estimate_workspace_id: null,
    project_name: "Customer project",
    quote_number: "Q-2026-001",
    customer_name: "Customer",
    customer_email: "customer@example.com",
    customer_phone: null,
    site_address: "100 Main Street",
    scope_summary: "Quoted work",
    line_items: [{ description: "Work", quantity: "1", unit: "LS", unit_price: "12000", amount: "12000" }],
    assumptions: [],
    exclusions: [],
    subtotal: "12000.00",
    gst_rate: "5.00",
    gst: "600.00",
    total: "12600.00",
    quote_date: "2026-08-21",
    valid_until: "2026-09-20",
    status: "draft",
    record_revision: 1,
    notes: null,
    created_by: "admin@ironhousecontracting.com",
    sent_at: null,
    issue_status: "draft",
    approved_revision: null,
    approved_at: null,
    approved_by: null,
    issued_at: null,
    issued_by: null,
    issuance_method: null,
    issuance_reference: null,
    accepted_at: null,
    accepted_by: null,
    acceptance_reference: null,
    acceptance_note: null,
    closed_at: null,
    job_number: null,
    created_at: "2026-08-21T00:00:00Z",
    updated_at: "2026-08-21T00:00:00Z",
    ...overrides,
  };
}

function project(overrides: Partial<Project>): Project {
  return {
    id: "project-1",
    name: "Project",
    client_owner: null,
    municipality: null,
    project_number: null,
    tender_number: null,
    tender_source: null,
    tender_closing_date: null,
    bid_due_date: null,
    estimated_construction_start: null,
    estimated_construction_finish: null,
    project_address: null,
    latitude: null,
    longitude: null,
    contract_value: null,
    status: "opportunity",
    notes: null,
    metadata: {},
    workspace_root: null,
    workspace_provisioned_at: null,
    supplier_ids: [],
    created_at: "2026-08-21T00:00:00Z",
    updated_at: "2026-08-21T00:00:00Z",
    ...overrides,
  };
}

function launchDashboard(job: Project, status: "ready" | "not_ready"): ProjectLaunchDashboard {
  return {
    project_id: job.id,
    job_number: job.project_number ?? "IH-2026-000",
    mobilization_status: status,
    checklist_completed_count: status === "ready" ? 10 : 3,
    checklist_total_count: 10,
    next_incomplete_control: status === "ready" ? null : {
      code: "contacts_authority",
      category: "Administration",
      label: "Confirm project contacts and authority limits.",
    },
    estimate_workspace_count: 1,
    priced_estimate_available: true,
    baseline_budget_total: 100000,
    budget_entry_count: 5,
    po_request_count: 2,
    pending_po_request_count: 1,
    safety_record_counts: { safety_permit: 1 },
    safety_release_status: "blocked",
    safety_requirement_count: 6,
    safety_folder_status: "prepared",
    portal_access_status: "not_started",
    portal_assignment_count: 0,
    document_count: 4,
    award_baseline_source: "Q-2026-001",
    award_pricing_subtotal: 100000,
    award_cost_budget_status: "needs_cost_allocation",
    uncoded_award_line_count: 5,
    procurement_requirement_count: 2,
    procurement_plan_status: "draft",
  };
}
