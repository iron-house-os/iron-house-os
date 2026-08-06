import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BackupsIntake, backupsApi } from "../api/backups";
import { financeApi } from "../api/finance";
import { BackupsReviewQueues } from "./BackupsReviewQueues";

vi.mock("../api/backups", () => ({ backupsApi: { updateDestination: vi.fn() } }));
vi.mock("../api/finance", () => ({ financeApi: { getBackupsReview: vi.fn() } }));
vi.mock("../api/media", () => ({ mediaApi: { contentUrl: vi.fn((id: string) => `/private-media/${id}`) } }));

const intake: BackupsIntake = {
  id: "intake-finance", media_id: "media-finance", media_hash: "a".repeat(64), uploader_id: "user-1",
  uploader_email: "crew@example.com", uploader_role: "foreman", upload_timestamp: "2026-08-06T10:00:00Z",
  note: null, project_hint: null, status: "routed", detected_type: "receipt", confidence: 0.94,
  classification_source: "local_ocr", review_destination: "finance_intake", routing_version: 0,
  destination_type: null, destination_record_id: null, error: null, sensitive_quarantine: false, attempt_count: 1,
  last_attempt_at: "2026-08-06T10:01:00Z", processing_started_at: "2026-08-06T10:01:00Z",
  processed_at: "2026-08-06T10:02:00Z", routed_at: "2026-08-06T10:02:00Z", failed_at: null,
  created_at: "2026-08-06T10:00:00Z", updated_at: "2026-08-06T10:02:00Z", audit_history: [],
};

describe("BackupsReviewQueues", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(financeApi.getBackupsReview).mockResolvedValue({ items: [intake], total: 1 });
  });

  it("shows separate review-only Finance sections and routes without finance actions", async () => {
    const user = userEvent.setup();
    vi.mocked(backupsApi.updateDestination).mockResolvedValue({ ...intake, review_destination: "finance_packing_slips", routing_version: 1 });
    render(<BackupsReviewQueues />);

    expect(await screen.findByRole("heading", { name: "Finance intake" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Receipts" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Invoices" })).toBeInTheDocument();
    const packing = screen.getByRole("heading", { name: "Packing Slips" }).closest("section");
    expect(packing).not.toBeNull();
    expect(within(packing as HTMLElement).getByText(/does not confirm quantity, quality, acceptance, or project cost/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve|pay|accept|export|reconcile/i })).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Review destination for intake-finance"), "finance_packing_slips");
    await waitFor(() => expect(backupsApi.updateDestination).toHaveBeenCalledWith("intake-finance", "finance_packing_slips", 0));
    expect(within(packing as HTMLElement).getByAltText("Private Backups original")).toBeInTheDocument();
  });
});
