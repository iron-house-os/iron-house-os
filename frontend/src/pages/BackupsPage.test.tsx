import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BackupsIntake, backupsApi } from "../api/backups";
import { mediaApi } from "../api/media";
import { BackupsPage } from "./BackupsPage";

const auth = vi.hoisted(() => ({ role: "viewer" }));

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { role: auth.role } }),
}));
vi.mock("../api/backups", () => ({
  backupsApi: {
    list: vi.fn(),
    create: vi.fn(),
    retry: vi.fn(),
    runDaily: vi.fn(),
  },
}));
vi.mock("../api/media", () => ({
  mediaApi: {
    upload: vi.fn(),
    contentUrl: vi.fn((id: string) => `/private-media/${id}`),
  },
}));

const intake: BackupsIntake = {
  id: "intake-1",
  media_id: "media-1",
  media_hash: "a".repeat(64),
  uploader_id: "user-1",
  uploader_email: "crew@example.com",
  uploader_role: "foreman",
  upload_timestamp: "2026-08-05T12:00:00Z",
  note: "Fuel receipt",
  project_hint: "Main Street",
  status: "pending",
  detected_type: null,
  confidence: null,
  classification_source: null,
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
  audit_history: [],
};

describe("BackupsPage", () => {
  beforeEach(() => {
    auth.role = "viewer";
    vi.clearAllMocks();
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:preview"),
      revokeObjectURL: vi.fn(),
    });
    vi.mocked(backupsApi.list).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(mediaApi.upload).mockResolvedValue([{ id: "media-1" }] as never);
    vi.mocked(backupsApi.create).mockResolvedValue(intake);
  });

  it("accepts exactly one camera image and registers its private media ID", async () => {
    const user = userEvent.setup();
    render(<BackupsPage />);

    const input = screen.getByLabelText("Photo") as HTMLInputElement;
    expect(input.multiple).toBe(false);
    expect(input.accept).toBe("image/*");
    expect(input.getAttribute("capture")).toBe("environment");

    const file = new File(["image"], "receipt.jpg", { type: "image/jpeg" });
    await user.upload(input, file);
    await user.type(screen.getByLabelText("Optional note"), "Fuel receipt");
    await user.type(screen.getByLabelText("Optional project hint"), "Main Street");
    await user.click(screen.getByRole("button", { name: "Store photo in Backups" }));

    await waitFor(() => expect(mediaApi.upload).toHaveBeenCalledWith({
      files: [file],
      caption: "Fuel receipt",
      category: "backup",
    }));
    expect(backupsApi.create).toHaveBeenCalledWith({
      media_id: "media-1",
      note: "Fuel receipt",
      project_hint: "Main Street",
    });
    expect(await screen.findByRole("status")).toHaveTextContent("daily controller");
  });

  it("shows meaningful classification diagnostics instead of a fixed fallback confidence", async () => {
    auth.role = "admin";
    vi.mocked(backupsApi.list).mockResolvedValue({
      items: [{
        ...intake,
        status: "needs_review",
        detected_type: "other",
        confidence: 0,
        classification_source: "local_ocr_provider_fallback",
      }],
      total: 1,
    });
    render(<BackupsPage />);

    expect(await screen.findByText("other · 0% confidence")).toBeInTheDocument();
    expect(screen.getByText("Classification source: Local OCR fallback")).toBeInTheDocument();
    expect(screen.queryByText(/25% confidence/)).not.toBeInTheDocument();
  });

  it("shows only management controls for the company queue", async () => {
    auth.role = "admin";
    vi.mocked(backupsApi.list).mockResolvedValue({ items: [intake], total: 1 });
    vi.mocked(backupsApi.runDaily).mockResolvedValue({ claimed: 1, routed: 0, needs_review: 1, failed: 0 });
    render(<BackupsPage />);

    expect(await screen.findByRole("heading", { name: "Company queue" })).toBeInTheDocument();
    expect(screen.getByText(/crew@example.com/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /run daily controller/i }));
    await waitFor(() => expect(backupsApi.runDaily).toHaveBeenCalledOnce());
  });
});
