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
    configure: vi.fn(),
    removeConfiguration: vi.fn(),
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

  it("accepts development credentials only after sandbox confirmation and clears the inputs", async () => {
    const user = userEvent.setup();
    const unconfigured = { ...connected, connected: false, configured: false, enabled: false, status: "not_connected" };
    vi.mocked(quickBooksApi.status).mockResolvedValue(unconfigured);
    vi.mocked(quickBooksApi.configure).mockResolvedValue({ ...unconfigured, configured: true, enabled: true });
    render(<QuickBooksConnectionCard />);

    const save = await screen.findByRole("button", { name: "Save sandbox credentials" });
    expect(save).toBeDisabled();
    await user.type(screen.getByLabelText("Development Client ID"), "sandbox-client-id");
    await user.type(screen.getByLabelText("Development Client Secret"), "sandbox-client-secret-value");
    await user.click(screen.getByRole("checkbox", { name: /development credentials/i }));
    await user.click(save);

    await waitFor(() => expect(quickBooksApi.configure).toHaveBeenCalledWith({
      client_id: "sandbox-client-id",
      client_secret: "sandbox-client-secret-value",
      sandbox_confirmed: true,
    }));
    expect(screen.queryByDisplayValue("sandbox-client-secret-value")).not.toBeInTheDocument();
    expect(await screen.findByRole("status")).toHaveTextContent("not displayed or stored in this browser");
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
