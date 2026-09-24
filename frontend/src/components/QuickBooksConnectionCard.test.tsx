import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { quickBooksApi } from "../api/quickBooks";
import { QuickBooksConnectionCard } from "./QuickBooksConnectionCard";

vi.mock("../api/quickBooks", () => ({
  quickBooksApi: {
    status: vi.fn(),
    startOAuth: vi.fn(),
    disconnect: vi.fn(),
  },
}));

const connected = {
  enabled: true,
  configured: true,
  connected: true,
  status: "connected",
  environment: "sandbox" as const,
  required_scope: "com.intuit.quickbooks.accounting",
  realm_id: "9341457990023688",
  company_name: "Sandbox Company US 3969",
  legal_name: "Sandbox Company US 3969",
  last_verified_at: "2026-09-24T01:00:00Z",
  last_error: null,
};

describe("QuickBooksConnectionCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.replaceState({}, "", "/finance");
  });

  it("labels the connection as sandbox-only and exposes no accounting write control", async () => {
    vi.mocked(quickBooksApi.status).mockResolvedValue(connected);
    render(<QuickBooksConnectionCard />);

    expect(await screen.findByText("Connected: Sandbox Company US 3969")).toBeInTheDocument();
    expect(screen.getByText("Sandbox only")).toBeInTheDocument();
    expect(screen.getByText(/cannot create or change accounting records/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /export|sync|create invoice/i })).not.toBeInTheDocument();
  });

  it("requires explicit confirmation before disconnecting", async () => {
    const user = userEvent.setup();
    vi.mocked(quickBooksApi.status).mockResolvedValue(connected);
    vi.mocked(quickBooksApi.disconnect).mockResolvedValue({
      ...connected,
      connected: false,
      status: "disconnected",
    });
    render(<QuickBooksConnectionCard />);

    const button = await screen.findByRole("button", { name: "Disconnect sandbox" });
    expect(button).toBeDisabled();
    await user.click(screen.getByRole("checkbox"));
    await user.click(button);

    await waitFor(() => expect(quickBooksApi.disconnect).toHaveBeenCalledTimes(1));
    expect(await screen.findByRole("status")).toHaveTextContent("Local tokens were cleared");
  });
});
