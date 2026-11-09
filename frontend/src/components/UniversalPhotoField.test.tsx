import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { UniversalPhotoField } from "./UniversalPhotoField";

const mocks = vi.hoisted(() => ({
  list: vi.fn(),
  upload: vi.fn(),
  link: vi.fn(),
  updateMetadata: vi.fn(),
  addVersion: vi.fn(),
  restore: vi.fn(),
}));

vi.mock("../api/media", () => ({
  mediaApi: {
    ...mocks,
    contentUrl: (assetId: string) => "/media/" + assetId + "/content",
  },
}));

const asset = {
  id: "asset-1",
  original_document_id: "document-1",
  current_version_id: "version-2",
  project_id: null,
  caption: "Pipe bedding",
  captured_date: "2026-08-01",
  location: null,
  category: "production_photo" as const,
  controlled: false,
  created_by_email: "editor@ironhousecontracting.com",
  links: [{ record_type: "field_record", record_id: "record-1" }],
  created_at: "2026-08-01T12:00:00Z",
  updated_at: "2026-08-01T12:10:00Z",
  versions: [
    {
      id: "version-2", asset_id: "asset-1", parent_version_id: "version-1",
      document_id: "document-2", version_number: 2, action: "edit" as const,
      editor_id: "user-1", editor_email: "editor@ironhousecontracting.com",
      operations: [{ type: "rotate" as const, values: { degrees: 90 } }],
      change_summary: "Corrected rotation", amendment_reason: null,
      created_at: "2026-08-01T12:10:00Z",
    },
    {
      id: "version-1", asset_id: "asset-1", parent_version_id: null,
      document_id: "document-1", version_number: 1, action: "original" as const,
      editor_id: "user-1", editor_email: "editor@ironhousecontracting.com",
      operations: [], change_summary: "Original upload retained", amendment_reason: null,
      created_at: "2026-08-01T12:00:00Z",
    },
  ],
};

describe("UniversalPhotoField", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.list.mockResolvedValue([asset]);
    mocks.link.mockImplementation(async () => asset);
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:preview"),
      revokeObjectURL: vi.fn(),
    });
  });

  it("opens the same full-screen viewer with transform, annotation and history controls", async () => {
    render(<UniversalPhotoField documentIds={["document-1"]} />);
    await userEvent.click(await screen.findByRole("button", { name: /pipe bedding/i }));

    expect(screen.getByRole("dialog", { name: /photo viewer and editor/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /zoom in/i })).toBeInTheDocument();
    expect(screen.getByTitle("Rotate")).toBeInTheDocument();
    expect(screen.getByTitle("Straighten")).toBeInTheDocument();
    expect(screen.getByTitle("Crop")).toBeInTheDocument();
    expect(screen.getByTitle("Draw")).toBeInTheDocument();
    expect(screen.getByTitle("Arrow")).toBeInTheDocument();
    expect(screen.getByTitle("Box")).toBeInTheDocument();
    expect(screen.getByTitle("Highlight")).toBeInTheDocument();
    expect(screen.getByTitle("Text")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "history" }));
    expect(screen.getByText("Version 2")).toBeInTheDocument();
    expect(screen.getByText("Version 1")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /restore as new version/i })).toBeInTheDocument();
  });

  it("retains a local capture and offers retry after upload failure", async () => {
    mocks.list.mockResolvedValue([]);
    mocks.upload.mockRejectedValue(new Error("Offline. Local selection retained."));
    render(<UniversalPhotoField recordType="equipment" recordId="equipment-1" category="equipment" />);

    const input = screen.getByLabelText(/take photos or choose multiple/i);
    const capture = new File(["photo"], "capture.jpg", { type: "image/jpeg" });
    fireEvent.change(input, { target: { files: [capture] } });
    await userEvent.click(screen.getByRole("button", { name: /upload photos/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Local selection retained"));
    expect(screen.getByText("1 ready to upload")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry upload/i })).toBeInTheDocument();
  });

  it("accumulates repeated camera captures instead of replacing the previous photo", () => {
    function Harness() {
      const [files, setFiles] = useState<File[]>([]);
      return <UniversalPhotoField files={files} onFilesChange={setFiles} category="flha" />;
    }
    render(<Harness />);

    const input = screen.getByLabelText("Take photos or choose multiple") as HTMLInputElement;
    const first = new File(["first"], "flha-1.jpg", { type: "image/jpeg", lastModified: 1 });
    const second = new File(["second"], "flha-2.jpg", { type: "image/jpeg", lastModified: 2 });
    fireEvent.change(input, { target: { files: [first] } });
    fireEvent.change(input, { target: { files: [second] } });

    expect(screen.getByText("2 ready to upload")).toBeInTheDocument();
    expect(screen.getByAltText("flha-1.jpg")).toBeInTheDocument();
    expect(screen.getByAltText("flha-2.jpg")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Remove flha-1.jpg" }));
    expect(screen.getByText("1 ready to upload")).toBeInTheDocument();
    expect(screen.queryByAltText("flha-1.jpg")).not.toBeInTheDocument();
  });
});
