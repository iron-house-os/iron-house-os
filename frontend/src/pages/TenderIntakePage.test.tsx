import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TenderIntakePage } from "./TenderIntakePage";

const tender = {
  id: "11111111-1111-4111-8111-111111111111",
  title: "Newton Watermain Replacement",
  tender_number: "T-2026-500",
  source: "manual",
  source_url: "https://example.com/tenders/T-2026-500",
  owner: "City of Surrey",
  municipality: "Surrey",
  closing_date: "2026-08-15",
  site_meeting_date: "2026-07-20",
  question_deadline: "2026-08-01",
  project_address: "72 Avenue and 152 Street",
  description: "Watermain, storm sewer, concrete restoration, and traffic control.",
  status: "new",
  estimated_value: 2400000,
  metadata: {},
  project_id: "22222222-2222-4222-8222-222222222222",
  rfq_package_id: "33333333-3333-4333-8333-333333333333",
  document_ids: ["44444444-4444-4444-8444-444444444444"],
  suggested_supplier_categories: ["pipe and fittings", "traffic control"],
  created_at: "2026-07-04T12:00:00Z",
  updated_at: "2026-07-04T12:00:00Z",
};

const project = {
  id: tender.project_id,
  name: tender.title,
  client_owner: tender.owner,
  municipality: tender.municipality,
  project_number: null,
  tender_number: tender.tender_number,
  tender_source: "manual",
  tender_closing_date: tender.closing_date,
  bid_due_date: tender.closing_date,
  estimated_construction_start: null,
  estimated_construction_finish: null,
  project_address: tender.project_address,
  latitude: null,
  longitude: null,
  contract_value: tender.estimated_value,
  status: "opportunity",
  notes: tender.description,
  metadata: {},
  supplier_ids: [],
  created_at: tender.created_at,
  updated_at: tender.updated_at,
};

const rfqPackage = {
  id: tender.rfq_package_id,
  title: "Newton Watermain Replacement RFQ Package",
  project_name: tender.title,
  scope_summary: tender.description,
  due_at: null,
  status: "draft",
  supplier_category_targets: tender.suggested_supplier_categories,
  metadata: {},
  recipients: [],
  documents: [],
  created_at: tender.created_at,
  updated_at: tender.updated_at,
};

const document = {
  id: tender.document_ids[0],
  title: "C-101 Utility Plan",
  category: "drawing",
  status: "registered",
  project_id: tender.project_id,
  rfq_package_id: tender.rfq_package_id,
  tender_id: tender.id,
  supplier_id: null,
  storage_uri: "drive://future/c-101.pdf",
  description: null,
  drawing: null,
  metadata: {},
  created_at: tender.created_at,
  updated_at: tender.updated_at,
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("TenderIntakePage", () => {
  it("renders tender list records", async () => {
    mockTenderApi();

    renderTenderWorkspace("/tenders");

    expect(await screen.findByText(tender.title)).toBeInTheDocument();
    expect(screen.getByText("Surrey")).toBeInTheDocument();
    expect(screen.getByText("2026-08-15")).toBeInTheDocument();
  });

  it("renders linked project, RFQ, documents, and supplier suggestions", async () => {
    mockTenderApi();

    renderTenderWorkspace(`/tenders/${tender.id}`);

    expect(await screen.findByRole("heading", { name: tender.title })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open Project Workspace" })).toBeInTheDocument();
    expect(screen.getAllByText("Newton Watermain Replacement RFQ Package").length).toBeGreaterThan(0);
    expect(screen.getByText("C-101 Utility Plan")).toBeInTheDocument();
    expect(screen.getByText("Pipe and fittings")).toBeInTheDocument();
    expect(screen.getByText("Traffic control")).toBeInTheDocument();
  });
});

function renderTenderWorkspace(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/tenders" element={<TenderIntakePage />} />
        <Route path="/tenders/:tenderId" element={<TenderIntakePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

function mockTenderApi() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith("/tenders")) {
        return jsonResponse({ items: [tender], total: 1 });
      }
      if (url.endsWith(`/tenders/${tender.id}`)) {
        return jsonResponse(tender);
      }
      if (url.endsWith(`/projects/${tender.project_id}`)) {
        return jsonResponse(project);
      }
      if (url.endsWith(`/rfqs/${tender.rfq_package_id}`)) {
        return jsonResponse(rfqPackage);
      }
      if (url.endsWith(`/documents?tender_id=${tender.id}`)) {
        return jsonResponse({ items: [document], total: 1 });
      }
      return jsonResponse({ detail: "Not found" }, 404);
    }),
  );
}

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}
