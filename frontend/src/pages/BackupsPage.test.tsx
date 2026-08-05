import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BackupsPage } from "./BackupsPage";
import { backupsApi } from "../api/backups";
import type { BackupIntake } from "../api/backups";

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { role: "viewer", email: "field@ironhousecontracting.com" } }),
}));
vi.mock("../api/backups", () => ({
  backupsApi: { list: vi.fn(), upload: vi.fn(), runDaily: vi.fn() },
}));

const intake: BackupIntake = {
  id: "intake-1", media_asset_id: "asset-1", media_sha256: "a".repeat(64),
  uploader_id: "user-1", uploader_email: "field@ironhousecontracting.com", uploader_role: "viewer",
  uploaded_at: "2026-08-05T12:00:00Z", note: "Delivery paperwork", project_hint: "Project 17",
  status: "pending", detected_type: null, confidence: null, destination_type: null,
  destination_record_id: null, error: null, sensitive_quarantine: false, classifier: null,
  attempt_count: 0, audit_history: [],
};

describe("BackupsPage", () => {
  beforeEach(() => {
    vi.mocked(backupsApi.list).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(backupsApi.upload).mockResolvedValue(intake);
  });

  it("accepts one camera image and submits the optional intake context", async () => {
    const user = userEvent.setup();
    render(<BackupsPage />);
    const input = screen.getByLabelText(/take photo or choose image/i) as HTMLInputElement;
    expect(input).not.toHaveAttribute("multiple");
    expect(input).toHaveAttribute("accept", "image/*");
    expect(input).toHaveAttribute("capture", "environment");

    const file = new File(["photo"], "delivery.jpg", { type: "image/jpeg" });
    await user.upload(input, file);
    fireEvent.change(screen.getByLabelText(/optional note/i), { target: { value: "Delivery paperwork" } });
    fireEvent.change(screen.getByLabelText(/optional project hint/i), { target: { value: "Project 17" } });
    await user.click(screen.getByRole("button", { name: /save original/i }));

    await waitFor(() => expect(backupsApi.upload).toHaveBeenCalledWith(file, "Delivery paperwork", "Project 17"));
    expect(screen.getByRole("status")).toHaveTextContent(/original saved/i);
    expect(screen.getByRole("heading", { name: "My submissions" })).toBeInTheDocument();
  });
});
