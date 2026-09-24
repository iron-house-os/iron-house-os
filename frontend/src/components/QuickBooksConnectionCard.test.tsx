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
  database_configured: true,
  connected: true,
  status: "connected",
  environment: "sandbox" as const,
  live_read_only_approved: false,
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
      environment_confirmed: true,
    }));
    expect(screen.queryByDisplayValue("sandbox-client-secret-value")).not.toBeInTheDocument();
    expect(await screen.findByRole("status")).toHaveTextContent("not displayed or stored in this browser");
  });

  it("clears the client secret after a failed configuration request", async () => {
    const user = userEvent.setup();
    const unconfigured = { ...connected, connected: false, configured: false, database_configured: false, enabled: false, status: "not_connected" };
    vi.mocked(quickBooksApi.status).mockResolvedValue(unconfigured);
    vi.mocked(quickBooksApi.configure).mockRejectedValue(new Error("Credentials rejected"));
    render(<QuickBooksConnectionCard />);

    await user.type(await screen.findByLabelText("Development Client ID"), "sandbox-client-id");
    await user.type(screen.getByLabelText("Development Client Secret"), "sandbox-client-secret-value");
    await user.click(screen.getByRole("checkbox", { name: /development credentials/i }));
    await user.click(screen.getByRole("button", { name: "Save sandbox credentials" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Credentials rejected");
    expect(screen.getByLabelText("Development Client Secret")).toHaveValue("");
  });

  it("requires the separate live acknowledgement before saving production credentials", async () => {
    const user = userEvent.setup();
    const unconfigured = {
      ...connected,
      connected: false,
      configured: false,
      database_configured: false,
      enabled: false,
      environment: "production" as const,
      live_read_only_approved: true,
      status: "not_connected",
    };
    vi.mocked(quickBooksApi.status).mockResolvedValue(unconfigured);
    vi.mocked(quickBooksApi.configure).mockResolvedValue({
      ...unconfigured,
      configured: true,
      database_configured: true,
      enabled: true,
    });
    render(<QuickBooksConnectionCard />);

    const save = await screen.findByRole("button", { name: "Save live credentials" });
    expect(save).toBeDisabled();
    await user.type(screen.getByLabelText("Production Client ID"), "production-client-id");
    await user.type(
      screen.getByLabelText("Production Client Secret"),
      "production-client-secret-value",
    );
    await user.click(screen.getByRole("checkbox", { name: /production credentials/i }));
    await user.click(save);

    await waitFor(() => expect(quickBooksApi.configure).toHaveBeenCalledWith({
      client_id: "production-client-id",
      client_secret: "production-client-secret-value",
      environment_confirmed: true,
    }));
    expect(screen.queryByDisplayValue("production-client-secret-value")).not.toBeInTheDocument();
  });

  it("only offers credential removal for database-managed credentials", async () => {
    vi.mocked(quickBooksApi.status).mockResolvedValue({
      ...connected,
      connected: false,
      database_configured: false,
      status: "not_connected",
    });
    render(<QuickBooksConnectionCard />);

    expect(await screen.findByText("Ready to connect a sandbox company.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remove sandbox credentials" })).not.toBeInTheDocument();
  });

  it("removes database-managed credentials only after confirmation", async () => {
    const user = userEvent.setup();
    const saved = { ...connected, connected: false, database_configured: true, status: "not_connected" };
    vi.mocked(quickBooksApi.status).mockResolvedValue(saved);
    vi.mocked(quickBooksApi.removeConfiguration).mockResolvedValue({
      ...saved,
      configured: false,
      database_configured: false,
      enabled: false,
    });
    render(<QuickBooksConnectionCard />);

    const remove = await screen.findByRole("button", { name: "Remove sandbox credentials" });
    expect(remove).toBeDisabled();
    await user.click(screen.getByRole("checkbox", { name: /remove the saved QuickBooks sandbox credentials/i }));
    await user.click(remove);

    await waitFor(() => expect(quickBooksApi.removeConfiguration).toHaveBeenCalledTimes(1));
    expect(await screen.findByRole("status")).toHaveTextContent("removed from IHOS");
  });

  it("labels the connection as sandbox-only and exposes no accounting write control", async () => {
    vi.mocked(quickBooksApi.status).mockResolvedValue(connected);
    render(<QuickBooksConnectionCard />);

    expect(await screen.findByText("Connected: Sandbox Company US 3969")).toBeInTheDocument();
    expect(screen.getByText("Sandbox only")).toBeInTheDocument();
    expect(screen.getByText(/cannot create or change accounting records/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /export|sync|create invoice/i })).not.toBeInTheDocument();
  });

  it("labels live mode as IHOS read-only while warning that Intuit scope is broader", async () => {
    vi.mocked(quickBooksApi.status).mockResolvedValue({
      ...connected,
      environment: "production",
      company_name: "Iron House Contracting Ltd.",
      legal_name: "Iron House Contracting Ltd.",
    });
    render(<QuickBooksConnectionCard />);

    expect(await screen.findByText("Connected: Iron House Contracting Ltd.")).toBeInTheDocument();
    expect(screen.getByText("Live · IHOS read-only")).toBeInTheDocument();
    expect(screen.getByText(/Intuit's accounting permission is broader/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /export|sync|create invoice/i })).not.toBeInTheDocument();
  });

  it("does not accept production credentials before the live approval gate", async () => {
    vi.mocked(quickBooksApi.status).mockResolvedValue({
      ...connected,
      connected: false,
      configured: false,
      database_configured: false,
      enabled: false,
      environment: "production",
      live_read_only_approved: false,
      status: "not_connected",
    });
    render(<QuickBooksConnectionCard />);

    expect(await screen.findByText(/awaiting owner-approved production activation/i)).toBeInTheDocument();
    expect(screen.queryByLabelText("Production Client Secret")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Connect live company" })).toBeDisabled();
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
