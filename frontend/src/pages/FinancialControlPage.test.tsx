import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BackupsIntake } from "../api/backups";
import { financeApi } from "../api/finance";
import { projectsApi } from "../api/projects";
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
    window.localStorage.clear();
    window.history.replaceState({}, "", "/finance");
    vi.mocked(financeApi.getStartupExpenses).mockResolvedValue({ total_startup_costs: 0, owner_loan_payable: 0, reimbursed_to_owner: 0, pending_review: 0, approved_unreimbursed: 0, entries: [] });
    vi.mocked(financeApi.getBackupsReview).mockImplementation(async (destination) => ({ items: destination === "finance_packing_slips" ? [item] : [], total: destination === "finance_packing_slips" ? 1 : 0 }));
  });

  it("shows separate review-only intake, receipt, invoice, and packing-slip sections", async () => {
    renderFinancial("/finance");
    expect(await screen.findByRole("heading", { name: "Backups review queues" })).toBeInTheDocument();
    for (const name of ["Finance intake", "Receipts", "Invoices", "Packing Slips"]) expect(screen.getByRole("heading", { name })).toBeInTheDocument();
    expect(screen.getByText(/quantity, quality, delivery acceptance, and project cost are not confirmed/i)).toBeInTheDocument();
    await waitFor(() => expect(financeApi.getBackupsReview).toHaveBeenCalledTimes(4));
    expect(screen.getByRole("img", { name: "Private Backups Packing Slips original" })).toHaveAttribute("src", "/private-media/media-1");
  });

  it("opens the linked project financial summary from workflow context", async () => {
    window.history.replaceState({}, "", "/finance?projectId=project-7&projectName=Linked+Job");
    vi.mocked(projectsApi.list).mockResolvedValue({
      items: [{ id: "project-7", name: "Linked Job" }],
      total: 1,
    } as never);
    vi.mocked(financeApi.getProject).mockResolvedValue({
      project_id: "project-7",
      project_name: "Linked Job",
      contract_value: 0,
      budget: 0,
      committed: 0,
      actual: 0,
      forecast_cost: 0,
      cost_variance: 0,
      forecast_profit: 0,
      forecast_margin_percent: 0,
      entries: [],
      cost_codes: [],
    });

    renderFinancial("/finance?projectId=project-7&projectName=Linked+Job");

    expect(await screen.findByRole("combobox", { name: "Project" })).toHaveValue("project-7");
    await waitFor(() => expect(financeApi.getProject).toHaveBeenCalledWith("project-7"));
  });

  it("updates the financial summary when the routed project changes without unmounting", async () => {
    const user = userEvent.setup();
    vi.mocked(projectsApi.list).mockResolvedValue({
      items: [
        { id: "project-7", name: "Linked Job" },
        { id: "project-8", name: "Second Job" },
      ],
      total: 2,
    } as never);
    vi.mocked(financeApi.getProject).mockImplementation(async (projectId) => ({
      project_id: projectId,
      project_name: projectId === "project-7" ? "Linked Job" : "Second Job",
      contract_value: 0,
      budget: 0,
      committed: 0,
      actual: 0,
      forecast_cost: 0,
      cost_variance: 0,
      forecast_profit: 0,
      forecast_margin_percent: 0,
      entries: [],
      cost_codes: [],
    }));

    render(
      <MemoryRouter initialEntries={["/finance?projectId=project-7&projectName=Linked+Job"]}>
        <FinancialRouteHarness />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("combobox", { name: "Project" })).toHaveValue("project-7");
    await user.click(screen.getByRole("button", { name: "Open second project" }));

    await waitFor(() => expect(screen.getByRole("combobox", { name: "Project" })).toHaveValue("project-8"));
    await waitFor(() => expect(financeApi.getProject).toHaveBeenCalledWith("project-8"));
  });
});

function renderFinancial(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><FinancialControlPage /></MemoryRouter>);
}

function FinancialRouteHarness() {
  const navigate = useNavigate();
  return <>
    <button type="button" onClick={() => navigate("/finance?projectId=project-8&projectName=Second+Job")}>Open second project</button>
    <FinancialControlPage />
  </>;
}
