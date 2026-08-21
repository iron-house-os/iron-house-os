import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DraftSaveIndicator } from "../components/DraftSaveIndicator";
import { useWorkflowDraft } from "./useWorkflowDraft";

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function Harness({ recoverLocal = true }: { recoverLocal?: boolean }) {
  const [value, setValue] = useState("");
  const draft = useWorkflowDraft({
    workflowType: "purchase_order_request",
    title: "Test PO",
    payload: { value },
    ready: true,
    enabled: Boolean(value),
    recoverLocal,
    onRestore: (saved) => setValue(typeof saved.value === "string" ? saved.value : ""),
  });
  return (
    <>
      <label>Purpose<input aria-label="Purpose" value={value} onChange={(event) => setValue(event.target.value)} /></label>
      <DraftSaveIndicator status={draft.status} lastSavedAt={draft.lastSavedAt} />
    </>
  );
}

describe("useWorkflowDraft", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/");
    window.localStorage.clear();
    vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const body = JSON.parse(String(init?.body));
      return jsonResponse({
        id: "draft-1",
        owner_account_id: "owner-1",
        project_id: null,
        workflow_type: body.workflow_type,
        title: body.title,
        payload: body.payload,
        schema_version: 1,
        revision: 1,
        status: "active",
        last_saved_at: "2026-08-21T06:30:00Z",
        created_at: "2026-08-21T06:30:00Z",
        updated_at: "2026-08-21T06:30:00Z",
      }, 201);
    }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("keeps an immediate local recovery copy and then saves the draft to IHOS", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.type(screen.getByLabelText("Purpose"), "Pipe and fittings");

    expect(window.localStorage.getItem("ihos:draft-recovery:purchase_order_request")).toContain("Pipe and fittings");
    expect(await screen.findByText(/Draft saved/)).toBeInTheDocument();
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    expect(window.localStorage.getItem("ihos:draft-recovery:purchase_order_request")).toBeNull();
    expect(window.location.search).toContain("draftId=draft-1");
  });

  it("recovers the latest device copy before a server save is available", async () => {
    window.localStorage.setItem(
      "ihos:draft-recovery:purchase_order_request",
      JSON.stringify({ payload: { value: "Recovered valves" }, savedAt: "2026-08-21T06:25:00Z" }),
    );

    render(<Harness />);

    expect(await screen.findByDisplayValue("Recovered valves")).toBeInTheDocument();
    expect(screen.getByText("Recovered unsaved work from this device")).toBeInTheDocument();
  });

  it("can preserve an explicitly targeted record instead of restoring a device buffer", async () => {
    window.localStorage.setItem(
      "ihos:draft-recovery:purchase_order_request",
      JSON.stringify({ payload: { value: "Unrelated recovered valves" }, savedAt: "2026-08-21T06:25:00Z" }),
    );

    render(<Harness recoverLocal={false} />);

    await waitFor(() => expect(screen.getByLabelText("Purpose")).toHaveValue(""));
    expect(screen.queryByText("Recovered unsaved work from this device")).not.toBeInTheDocument();
  });
});
