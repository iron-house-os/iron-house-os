import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BackupsIntake } from "../api/backups";
import { financeApi } from "../api/finance";
import { FinancialControlPage } from "./FinancialControlPage";

vi.mock("../api/finance", () => ({ financeApi: { getBackupsReview: vi.fn(), getStartupExpenses: vi.fn(), getCustomerInvoices: vi.fn(() => Promise.resolve({ items: [], total: 0 })), getProject: vi.fn(), importEstimate: vi.fn(), createEntry: vi.fn(), createStartupExpense: vi.fn(), updateStartupExpense: vi.fn(), startupQuickBooksUrl: vi.fn(() => "#"), quickBooksUrl: vi.fn(() => "#"), customerInvoicePdfUrl: vi.fn(() => "#") } }));
vi.mock("../api/projects", () => ({ projectsApi: { list: vi.fn(() => Promise.resolve({ items: [] })) } }));
vi.mock("../api/media", () => ({ mediaApi: { contentUrl: vi.fn((id: string) => `/private-media/${id}`), upload: vi.fn(), link: vi.fn() } }));
vi.mock("../components/ReceiptCapturePanel", () => ({ ReceiptCapturePanel: () => <div>Controlled receipt workflow</div> }));
vi.mock("../components/UniversalPhotoField", () => ({ UniversalPhotoField: () => <div>Photo field</div> }));

const item: BackupsIntake = {
  id: "intake-1", media_id: "media-1", media_hash: "a".repeat(64), uploader_id: "user-1", uploader_email: "crew@example.com", uploader_role: "foreman", upload_timestamp: "2026-08-06T10:00:00Z", note: null, project_hint: "Main Street", status: "routed", detected_type: "packing_slip", confidence: 0.94, classification_source: "local_ocr", review_destination: "finance_packing_slips", destination_type: null, destination_record_id: null, error: null, sensitive_quarantine: false, attempt_count: 1, last_attempt_at: "2026-08-06T10:01:00Z", processing_started_at: "2026-08-06T10:01:00Z", processed_at: "2026-08-06T10:02:00Z", routed_at: "2026-08-06T10:02:00Z", failed_at: null, created_at: "2026-08-06T10:00:00Z", updated_at: "2026-08-06T10:02:00Z", audit_history: [],
};

describe("FinancialControlPage Backups queues", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(financeApi.getStartupExpenses).mockResolvedValue({ total_startup_costs: 0, owner_loan_payable: 0, reimbursed_to_owner: 0, pending_review: 0, approved_unreimbursed: 0, entries: [] });
    vi.mocked(financeApi.getBackupsReview).mockImplementation(async (destination) => ({ items: destination === "finance_packing_slips" ? [item] : [], total: destination === "finance_packing_slips" ? 1 : 0 }));
  });

  it("shows separate review-only intake, receipt, invoice, and packing-slip sections", async () => {
    render(<FinancialControlPage />);
    expect(await screen.findByRole("heading", { name: "Backups review queues" })).toBeInTheDocument();
    for (const name of ["Finance intake", "Receipts", "Invoices", "Packing Slips"]) expect(screen.getByRole("heading", { name })).toBeInTheDocument();
    expect(screen.getByText(/quantity, quality, delivery acceptance, and project cost are not confirmed/i)).toBeInTheDocument();
    await waitFor(() => expect(financeApi.getBackupsReview).toHaveBeenCalledTimes(4));
    expect(screen.getByRole("img", { name: "Private Backups Packing Slips original" })).toHaveAttribute("src", "/private-media/media-1");
  });
});
