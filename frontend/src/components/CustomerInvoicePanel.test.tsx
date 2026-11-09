import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { financeApi } from "../api/finance";
import { CustomerInvoicePanel } from "./CustomerInvoicePanel";

vi.mock("../api/finance", () => ({ financeApi: {
  getCustomerInvoices: vi.fn(),
  getQuickBooksInvoicePreview: vi.fn(),
  customerInvoicePdfUrl: vi.fn(() => "#"),
} }));

describe("CustomerInvoicePanel QuickBooks preview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(financeApi.getCustomerInvoices).mockResolvedValue({ items: [{
      id: "invoice-1", invoice_number: "IHC-1", project_id: "project-1", project_name: "Job",
      site_address: null, customer_name: "Customer", customer_address: "123 Main", customer_phone: null,
      invoice_date: "2026-09-01", due_date: "2026-10-01", terms: "Net 30", status: "issued",
      line_items: [], subtotal: "100.00", gst_rate: "5", gst: "5.00", total: "105.00", development_seed_key: null,
    }], total: 1 });
  });

  it("shows source blockers without offering an accounting transfer", async () => {
    vi.mocked(financeApi.getQuickBooksInvoicePreview).mockResolvedValue({
      invoice_id: "invoice-1", invoice_number: "IHC-1", customer_name: "Customer", project_id: "project-1",
      invoice_date: "2026-09-01", due_date: "2026-10-01", status: "issued", subtotal: "100.00", gst: "5.00",
      total: "105.00", line_items: [], source_checks_passed: false,
      blockers: ["Invoice lines, GST and total must reconcile exactly before export."],
      accounting_setup_required: ["Connect the sandbox company."], export_enabled: false,
    });
    const user = userEvent.setup();
    render(<CustomerInvoicePanel />);
    await user.click(await screen.findByRole("button", { name: "QuickBooks preview" }));
    expect(financeApi.getQuickBooksInvoicePreview).toHaveBeenCalledWith("invoice-1");
    expect(await screen.findByText(/Invoice lines, GST and total must reconcile exactly/)).toBeInTheDocument();
    expect(screen.getByText(/Accounting export is not enabled/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /export|sync|post/i })).not.toBeInTheDocument();
  });
});
