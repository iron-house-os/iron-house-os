import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Project, ProjectDashboard } from "../api/projects";
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

afterEach(() => {
  vi.restoreAllMocks();
});

describe("ProjectWorkspacePage", () => {
  it("renders the project list with project summary columns", async () => {
    mockProjectApi();

    renderWorkspace("/projects");

    expect(await screen.findByText(project.name)).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Ready" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Docs" })).toBeInTheDocument();
    expect(await screen.findByText("80%")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
  });

  it("loads project detail from the route", async () => {
    mockProjectApi();

    renderWorkspace(`/projects/${project.id}`);

    expect(await screen.findByRole("heading", { name: project.name })).toBeInTheDocument();
    expect(screen.getByText("City of Surrey - Surrey")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Archive" })).toBeInTheDocument();
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

function mockProjectApi() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = input.toString();

    if (url.endsWith("/projects")) {
      return jsonResponse({ items: [project], total: 1 });
    }

    if (url.endsWith(`/projects/${project.id}/dashboard`)) {
      return jsonResponse(dashboard);
    }

    if (url.endsWith(`/projects/${project.id}`)) {
      return jsonResponse(project);
    }

    return jsonResponse({ detail: "Not found" }, 404);
  });

  vi.stubGlobal("fetch", fetchMock);
}

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}
