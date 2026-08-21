import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CustomerQuotesPage } from "./CustomerQuotesPage";

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "admin-1", email: "admin@ironhousecontracting.com", role: "admin" },
  }),
}));

const quoteBodies: Record<string, unknown>[] = [];
let savedQuote: Record<string, unknown> | null = null;

function json(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function quote(status: "draft" | "sent" | "accepted" | "declined" | "expired", revision: number) {
  return {
    id: "quote-1",
    project_id: "project-1",
    project_name: "Smith drainage repair",
    quote_number: "Q-2026-001",
    customer_name: "Alex Smith",
    customer_email: null,
    customer_phone: null,
    site_address: null,
    scope_summary: "Replace failed storm service",
    line_items: [{ description: "Pipe replacement", quantity: "1", unit: "LS", unit_price: "10000.00", amount: "10000.00" }],
    assumptions: [],
    exclusions: [],
    subtotal: "10000.00",
    gst_rate: "5.0000",
    gst: "500.00",
    total: "10500.00",
    quote_date: "2026-08-21",
    valid_until: null,
    status,
    record_revision: revision,
    notes: null,
    created_by: "admin@ironhousecontracting.com",
    sent_at: null,
    accepted_at: status === "accepted" ? "2026-08-21T12:00:00Z" : null,
    accepted_by: status === "accepted" ? "admin@ironhousecontracting.com" : null,
    acceptance_reference: status === "accepted" ? "Customer email" : null,
    acceptance_note: null,
    closed_at: status === "accepted" ? "2026-08-21T12:00:00Z" : null,
    job_number: status === "accepted" ? "IH-2026-001" : null,
    created_at: "2026-08-21T11:00:00Z",
    updated_at: "2026-08-21T12:00:00Z",
  };
}

describe("CustomerQuotesPage", () => {
  beforeEach(() => {
    quoteBodies.length = 0;
    savedQuote = null;
    window.localStorage.clear();
    window.history.replaceState({}, "", "/customer-quotes");
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/customer-quotes") && !init?.method) {
        return json({ items: savedQuote ? [savedQuote] : [], total: savedQuote ? 1 : 0 });
      }
      if (url.endsWith("/customer-quotes") && init?.method === "POST") {
        quoteBodies.push(JSON.parse(String(init.body)));
        savedQuote = quote("draft", 1);
        return json(savedQuote, 201);
      }
      if (url.endsWith("/customer-quotes/quote-1") && init?.method === "PATCH") {
        const body = JSON.parse(String(init.body));
        quoteBodies.push(body);
        savedQuote = { ...quote("draft", 2), ...body, record_revision: 2 };
        return json(savedQuote);
      }
      if (url.endsWith("/accept") && init?.method === "POST") {
        quoteBodies.push(JSON.parse(String(init.body)));
        savedQuote = quote("accepted", 2);
        return json(savedQuote);
      }
      if (url.endsWith("/status") && init?.method === "POST") {
        const body = JSON.parse(String(init.body));
        quoteBodies.push(body);
        savedQuote = quote(body.status, 2);
        return json(savedQuote);
      }
      if (url.endsWith("/workflow-drafts") && init?.method === "POST") {
        const body = JSON.parse(String(init.body));
        return json({
          id: "workflow-draft-1",
          owner_account_id: "admin-1",
          project_id: null,
          workflow_type: "customer_quote",
          title: body.title,
          payload: body.payload,
          schema_version: 1,
          revision: 1,
          status: "active",
          last_saved_at: "2026-08-21T11:00:00Z",
          created_at: "2026-08-21T11:00:00Z",
          updated_at: "2026-08-21T11:00:00Z",
        }, 201);
      }
      if (url.includes("/workflow-drafts/") && init?.method === "PATCH") {
        const body = JSON.parse(String(init.body));
        return json({
          id: "workflow-draft-1",
          owner_account_id: "admin-1",
          project_id: null,
          workflow_type: "customer_quote",
          title: body.title,
          payload: body.payload,
          schema_version: 1,
          revision: body.expected_revision + 1,
          status: "active",
          last_saved_at: "2026-08-21T11:01:00Z",
          created_at: "2026-08-21T11:00:00Z",
          updated_at: "2026-08-21T11:01:00Z",
        });
      }
      if (url.endsWith("/complete") && init?.method === "POST") return json({});
      throw new Error(`Unexpected request: ${url}`);
    }));
  });

  afterEach(() => vi.unstubAllGlobals());

  it("captures verbal information and uses explicit management acceptance to create the job", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><CustomerQuotesPage /></MemoryRouter>);

    await screen.findByText("No customer quotes yet.");
    await user.type(screen.getByLabelText("Project / work name"), "Smith drainage repair");
    await user.type(screen.getByLabelText("Customer / company"), "Alex Smith");
    await user.type(screen.getByLabelText("Scope summary"), "Replace failed storm service");
    await user.type(screen.getByLabelText("Item 1"), "Pipe replacement");
    await user.type(screen.getByLabelText("Unit price 1"), "10000");

    await user.click(screen.getByRole("button", { name: "Save draft quote in IHOS" }));

    expect(await screen.findByText("Q-2026-001 saved in IHOS as draft.")).toBeInTheDocument();
    expect(screen.getByText("Not awarded")).toBeInTheDocument();
    expect(quoteBodies[0]).toEqual(expect.objectContaining({
      project_name: "Smith drainage repair",
      customer_name: "Alex Smith",
      scope_summary: "Replace failed storm service",
    }));

    await user.click(screen.getByRole("button", { name: "Accept / award" }));
    await user.type(screen.getByLabelText("Acceptance reference"), "Customer email");
    await user.click(screen.getByRole("button", { name: "Confirm acceptance and create job" }));

    expect(await screen.findByText("Q-2026-001 accepted — job IH-2026-001 created.")).toBeInTheDocument();
    expect(screen.getByText("IH-2026-001")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open Project Workspace/ })).toHaveAttribute("href", "/projects/project-1");
    await waitFor(() => expect(quoteBodies.at(-1)).toEqual(expect.objectContaining({ acceptance_reference: "Customer email" })));
  });

  it("opens a queued draft directly and records a sent quote decision", async () => {
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    savedQuote = quote("draft", 1);
    window.localStorage.setItem(
      "ihos:draft-recovery:customer_quote",
      JSON.stringify({
        payload: { projectName: "Unrelated device recovery", customerName: "Wrong customer" },
        savedAt: "2026-08-21T10:00:00Z",
      }),
    );
    const { unmount } = render(
      <MemoryRouter initialEntries={["/customer-quotes?quoteId=quote-1&action=edit"]}>
        <CustomerQuotesPage />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Edit Q-2026-001" })).toBeInTheDocument();
    expect(screen.getByLabelText("Project / work name")).toHaveValue("Smith drainage repair");
    expect(screen.getByLabelText("Customer / company")).toHaveValue("Alex Smith");
    unmount();

    savedQuote = quote("sent", 1);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/customer-quotes?quoteId=quote-1&action=decision"]}>
        <CustomerQuotesPage />
      </MemoryRouter>,
    );

    await user.click(await screen.findByRole("button", { name: "Mark declined" }));
    await waitFor(() => expect(screen.getByText("declined")).toBeInTheDocument());
    expect(quoteBodies.at(-1)).toEqual({ expected_revision: 1, status: "declined", note: null });
  });

  it.each(["declined", "expired"] as const)("starts a controlled revision from a %s quote", async (status) => {
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    savedQuote = quote(status, 1);
    const user = userEvent.setup();

    render(<MemoryRouter><CustomerQuotesPage /></MemoryRouter>);

    await user.click(await screen.findByRole("button", { name: "Start new revision" }));
    expect(screen.getByRole("heading", { name: "New revision Q-2026-001" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Accept / award" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Mark sent" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Mark declined" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Mark expired" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Save quote revision" }));

    expect(await screen.findByText("Q-2026-001 saved in IHOS as draft.")).toBeInTheDocument();
    expect(quoteBodies.at(-1)).toEqual(expect.objectContaining({ expected_revision: 1 }));
  });
});
