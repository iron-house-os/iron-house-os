import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LibraryDocument } from "../api/documents";
import { externalDriveUrl, ProjectDocumentBrowser } from "./ProjectDocumentBrowser";

const linkedDocument: LibraryDocument = {
  id: "12900000-0000-0000-0000-000000000001",
  title: "ITT-2602 Tender.pdf",
  category: "other",
  status: "registered",
  project_id: "12900000-0000-0000-0000-000000000002",
  rfq_package_id: null,
  tender_id: null,
  supplier_id: null,
  storage_uri: null,
  description: "Linked Google Drive source; the original remains immutable.",
  drawing: null,
  metadata: {
    drive_file_id: "drive-file-129",
    drive_url: "https://drive.google.com/file/d/drive-file-129/view",
    source_immutable: true,
  },
  created_at: "2026-08-02T00:00:00Z",
  updated_at: "2026-08-02T00:00:00Z",
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("ProjectDocumentBrowser", () => {
  it("shows a safe external Drive link without offering a local download", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ items: [linkedDocument], total: 1 })));

    render(<ProjectDocumentBrowser projectId={linkedDocument.project_id} />);

    const link = await screen.findByRole("link", { name: "Open in Drive" });
    expect(link).toHaveAttribute("href", linkedDocument.metadata.drive_url);
    expect(link).toHaveAttribute("target", "_blank");
    expect(screen.queryByRole("button", { name: "Download" })).not.toBeInTheDocument();
  });

  it("rejects non-Google and non-HTTPS metadata links", () => {
    expect(
      externalDriveUrl({ ...linkedDocument, metadata: { drive_url: "https://example.com/file" } }),
    ).toBeNull();
    expect(
      externalDriveUrl({ ...linkedDocument, metadata: { drive_url: "javascript:alert(1)" } }),
    ).toBeNull();
  });
});

function jsonResponse(body: unknown) {
  return { ok: true, status: 200, json: async () => body } as Response;
}
