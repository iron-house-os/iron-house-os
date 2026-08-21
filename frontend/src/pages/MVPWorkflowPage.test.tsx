import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MVPWorkflowPage } from "./MVPWorkflowPage";

const draft = {
  id: "draft-246",
  owner_account_id: "owner-1",
  project_id: "project-1",
  workflow_type: "purchase_order_request",
  title: "PO request — Pipe and fittings",
  payload: { purpose: "Pipe and fittings" },
  schema_version: 1,
  revision: 3,
  status: "active",
  last_saved_at: "2026-08-21T06:30:00Z",
  created_at: "2026-08-21T06:00:00Z",
  updated_at: "2026-08-21T06:30:00Z",
};

function response(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("MVPWorkflowPage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === "POST") return response({ ...draft, status: "cancelled", revision: 4 });
      return response({ items: [draft], total: 1 });
    }));
  });

  afterEach(() => vi.unstubAllGlobals());

  it("lists unfinished work with a direct resume link and audited discard action", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><MVPWorkflowPage /></MemoryRouter>);

    expect(await screen.findByText("PO request — Pipe and fittings")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Continue" })).toHaveAttribute(
      "href",
      "/request-po?draftId=draft-246&projectId=project-1",
    );

    await user.click(screen.getByRole("button", { name: "Discard" }));
    await waitFor(() => expect(screen.queryByText("PO request — Pipe and fittings")).not.toBeInTheDocument());
    expect(fetch).toHaveBeenLastCalledWith(
      expect.stringContaining("/workflow-drafts/draft-246/cancel"),
      expect.objectContaining({ method: "POST" }),
    );
  });
});
