import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { financeApi } from "../api/finance";
import { ReceiptCapturePanel } from "./ReceiptCapturePanel";

vi.mock("../api/finance", () => ({ financeApi: { getReceipts: vi.fn(), receiptAction: vi.fn(), exportReceipt: vi.fn(), updateReceipt: vi.fn(), createReceipt: vi.fn(), extractReceipt: vi.fn() } }));
vi.mock("../api/projects", () => ({ projectsApi: { list: vi.fn().mockResolvedValue({ items: [] }) } }));
vi.mock("../api/equipment", () => ({ equipmentApi: { list: vi.fn().mockResolvedValue({ items: [] }) } }));
vi.mock("../api/media", () => ({ mediaApi: { contentUrl: vi.fn(() => "/receipt.jpg"), upload: vi.fn() } }));
vi.mock("./UniversalPhotoField", () => ({ UniversalPhotoField: ({ label, onFilesChange }: { label: string; onFilesChange?: (files: File[]) => void }) => <div>{label}{onFilesChange ? <button type="button" onClick={() => onFilesChange([new File(["receipt"], "receipt.jpg", { type: "image/jpeg" })])}>Choose mock photo</button> : null}</div> }));

const blockedReceipt = {
  id: "receipt-1", status: "needs_review", submitter_email: "crew@example.com", media_asset_ids: ["asset-1"], vendor_id: null,
  vendor_name: "Civil Supply", vendor_address: null, reference: "R-1", receipt_date: "2026-08-02", receipt_time: null, currency: "CAD",
  subtotal: 100, discounts: 0, gst: 5, pst: 0, other_tax: 0, tip: 0, total: 110, payment_method: "card", card_brand: "Visa",
  card_last_four: "4242", company_card_id: null, employee_email: "crew@example.com", treatment: "company_card", confidence: { total: 0.4 },
  source_regions: { total: { page: 1, x: 0.6, y: 0.8, width: 0.3, height: 0.08 } }, flags: [], duplicate_of_id: null,
  approved_by: null, exported_by: null, version: 2, reconciliation_difference: -5, is_balanced: false,
  approval_blockers: ["Low-confidence field requires correction: total.", "Receipt total is out of balance by -5.00 CAD."],
  line_items: [{ id: "line-1", position: 1, description: "Diesel", normalized_description: "Diesel fuel", quantity: 1, unit_price: 100, tax: 5, line_total: 100, category: "fuel", project_id: null, equipment_id: null, cost_code: null, overhead_category: null, treatment: "company_card", confidence: 0.4, source_region: { page: 1, x: 0.1, y: 0.3, width: 0.7, height: 0.06 }, flags: [] }],
  audit_history: [],
};

describe("ReceiptCapturePanel", () => {
  beforeEach(() => { vi.clearAllMocks(); vi.mocked(financeApi.getReceipts).mockResolvedValue({ items: [], total: 0 }); });

  it("offers phone/gallery capture and line-item split coding without an approval action", async () => {
    const user = userEvent.setup(); render(<ReceiptCapturePanel />);
    expect(await screen.findByText("Submit a receipt")).toBeInTheDocument();
    expect(screen.getByText(/camera or gallery/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /add split/i }));
    expect(screen.getByRole("button", { name: "Remove line 2" })).toBeInTheDocument();
    vi.mocked((await import("../api/media")).mediaApi.upload).mockResolvedValue([{ id: "asset-ai" }] as never);
    vi.mocked(financeApi.extractReceipt).mockResolvedValue({ model: "gpt-test", draft: { media_asset_ids: ["asset-ai"], vendor_name: "Civil Supply", vendor_address: "100 Main St", reference: "R-7", receipt_date: "2026-08-02", receipt_time: "09:30", currency: "CAD", subtotal: 10, discounts: 0, gst: 0.5, pst: 0, other_tax: 0, tip: 0, total: 10.5, payment_method: "card", card_brand: "Visa", card_last_four: "4242", employee_email: null, treatment: "company_card", confidence: { vendor_name: 0.96, receipt_date: 0.95, subtotal: 0.94, total: 0.97 }, source_regions: {}, flags: [], line_items: [{ description: "Gloves", normalized_description: "Safety gloves", quantity: 1, unit_price: 10, tax: 0.5, line_total: 10, category: "ppe", project_id: null, equipment_id: null, cost_code: null, overhead_category: "general_overhead", treatment: "company_card", confidence: 0.91, source_region: null, flags: [] }] } });
    await user.click(screen.getByRole("button", { name: "Choose mock photo" }));
    await user.click(screen.getByRole("button", { name: "Extract receipt" }));
    expect(await screen.findByText(/AI draft extracted with gpt-test/)).toBeInTheDocument();
    expect(screen.getByLabelText("Vendor")).toHaveValue("Civil Supply");
    expect(financeApi.createReceipt).not.toHaveBeenCalled();
  });

  it("shows source highlights and disables approval for low-confidence, unbalanced receipts", async () => {
    vi.mocked(financeApi.getReceipts).mockResolvedValue({ items: [blockedReceipt], total: 1 } as never);
    render(<ReceiptCapturePanel reviewer />);
    expect(await screen.findByText("Low-confidence field requires correction: total.")).toBeInTheDocument();
    expect(screen.getByAltText("Receipt with extraction source highlights")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled());
    expect(screen.getByRole("button", { name: /correct extraction/i })).toBeEnabled();
  });
});
