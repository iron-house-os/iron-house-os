import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DrawingIntelligencePage } from "./DrawingIntelligencePage";

const projectId = "11111111-1111-4111-8111-111111111111";
const analysis = {
  analysis_version: "build-206-v1",
  source: {
    document_id: "22222222-2222-4222-8222-222222222222",
    project_id: projectId,
    storage_uri: "/data/project/civil.pdf",
    original_filename: "civil-ift.pdf",
    sha256_hash: "a".repeat(64),
    size_bytes: 4096,
    page_count: 2,
  },
  title: "Issued for Tender Civil Drawings",
  municipality: "Surrey",
  extraction_status: "completed",
  analyzed_at: "2026-07-13T16:00:00Z",
  text_character_count: 1400,
  pages: [
    {
      page_number: 1,
      character_count: 900,
      text_preview: "Quantity Schedule: 120 m of 300 mm PVC storm pipe.",
      extraction_warning: null,
    },
    {
      page_number: 2,
      character_count: 500,
      text_preview: "Field verify utility crossing.",
      extraction_warning: null,
    },
  ],
  quantity_candidates: [
    {
      description: "Quantity Schedule: 120 m of 300 mm PVC storm pipe",
      quantity: 120,
      unit: "m",
      page_number: 1,
      source_text: "Quantity Schedule: 120 m of 300 mm PVC storm pipe",
      confidence: "high",
      requires_verification: true,
    },
  ],
  constructability_issues: [
    {
      issue_type: "constructability",
      severity: "critical",
      title: "Potential utility conflict",
      detail: "A possible conflict needs coordinated review.",
      page_number: 2,
      evidence: "Field verify utility crossing.",
      requires_review: true,
    },
  ],
  municipal_standard_issues: [
    {
      issue_type: "municipal_standard",
      severity: "info",
      title: "Municipal standard edition requires verification",
      detail: "A standard reference was detected but compliance is not validated.",
      page_number: 1,
      evidence: "City of Surrey MMCD standard drawing.",
      requires_review: true,
    },
  ],
  warnings: [
    "Automated drawing findings are candidates only and require estimator or engineer verification.",
  ],
};

describe("DrawingIntelligencePage", () => {
  const requests: Array<{ url: string; method: string; body: BodyInit | null | undefined }> = [];

  beforeEach(() => {
    requests.length = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      requests.push({ url, method, body: init?.body });
      if (url.endsWith(`/drawing-intelligence/projects/${projectId}`)) {
        return new Response(JSON.stringify({ items: [], total: 0 }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (url.endsWith("/drawing-intelligence/ingest") && method === "POST") {
        return new Response(JSON.stringify(analysis), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        });
      }
      throw new Error(`Unexpected request: ${method} ${url}`);
    }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("ingests a project PDF and presents traceable candidates and review flags", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={[`/drawing-intelligence?projectId=${projectId}&projectName=King%20George`]}>
        <DrawingIntelligencePage />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Working project: King George")).toBeInTheDocument();
    expect(screen.getByDisplayValue(projectId)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Drawing municipality"), "Surrey");
    await user.type(
      screen.getByLabelText("Drawing set title"),
      "Issued for Tender Civil Drawings",
    );
    await user.upload(
      screen.getByLabelText("Civil PDF file"),
      new File(["%PDF-1.7"], "civil-ift.pdf", { type: "application/pdf" }),
    );
    await user.click(screen.getByRole("button", { name: "Ingest and analyze PDF" }));

    await waitFor(() => {
      expect(
        requests.some((item) => item.url.endsWith("/drawing-intelligence/ingest")),
      ).toBe(true);
    });

    expect(
      await screen.findByRole("heading", { name: "Quantity candidates" }),
    ).toBeInTheDocument();
    expect(screen.getByText("120 m")).toBeInTheDocument();
    expect(screen.getByText("Potential utility conflict")).toBeInTheDocument();
    expect(
      screen.getByText("Municipal standard edition requires verification"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Candidate quantities require verification/),
    ).toBeInTheDocument();
    expect(screen.getByText(`civil-ift.pdf · SHA-256 ${"a".repeat(64)}`)).toBeInTheDocument();

    await waitFor(() => {
      const request = requests.find((item) => item.url.endsWith("/drawing-intelligence/ingest"));
      expect(request?.method).toBe("POST");
      expect(request?.body).toBeInstanceOf(FormData);
      expect((request?.body as FormData).get("project_id")).toBe(projectId);
      expect((request?.body as FormData).get("municipality")).toBe("Surrey");
    });
  });
});
