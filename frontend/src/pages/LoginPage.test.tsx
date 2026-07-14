import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";

const userAccount = {
  id: "00000000-0000-0000-0000-000000000001",
  email: "jeremie@ironhousecivil.com",
  display_name: "Jeremie Peters",
  role: "admin",
  is_active: true,
  password_reset_required: false,
  last_login_at: null,
  created_at: "2026-07-14T00:00:00Z",
  updated_at: "2026-07-14T00:00:00Z",
};

describe("LoginPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("requires a session, signs in, and renders the authenticated shell", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/auth/me")) {
        return new Response(JSON.stringify({ detail: "Sign in is required." }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (url.endsWith("/auth/login")) {
        return new Response(
          JSON.stringify({ authentication: "authenticated", user: userAccount }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.endsWith("/projects")) {
        return new Response(JSON.stringify({ items: [], total: 0 }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <App />
      </MemoryRouter>,
    );

    await user.type(await screen.findByLabelText("Email"), "jeremie@ironhousecivil.com");
    await user.type(screen.getByLabelText("Password"), "correct-horse-battery-staple");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Signed in as Jeremie Peters")).toBeInTheDocument();
    expect(screen.getByText("admin")).toBeInTheDocument();
    expect(fetchMock.mock.calls.every(([, init]) => init?.credentials === "include")).toBe(true);
  });

  it("shows the generic API error when credentials are rejected", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        return new Response(
          JSON.stringify({ detail: url.endsWith("/auth/me") ? "Sign in is required." : "Email or password is incorrect." }),
          { status: 401, headers: { "Content-Type": "application/json" } },
        );
      }),
    );
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );

    await user.type(await screen.findByLabelText("Email"), "jeremie@ironhousecivil.com");
    await user.type(screen.getByLabelText("Password"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Email or password is incorrect.");
  });

  it("requires a permanent password after administrator-assisted recovery", async () => {
    const recoveryAccount = { ...userAccount, password_reset_required: true };
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/auth/me")) {
        return new Response(
          JSON.stringify({ authentication: "authenticated", user: recoveryAccount }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.endsWith("/auth/change-password")) {
        return new Response(
          JSON.stringify({
            authentication: "authenticated",
            user: { ...recoveryAccount, password_reset_required: false },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.endsWith("/projects")) {
        return new Response(JSON.stringify({ items: [], total: 0 }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Choose a permanent password")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Temporary password"), "temporary-password-2026");
    await user.type(screen.getByLabelText("New password"), "permanent-password-2026");
    await user.type(screen.getByLabelText("Confirm new password"), "permanent-password-2026");
    await user.click(screen.getByRole("button", { name: "Change password" }));

    expect(await screen.findByText("Signed in as Jeremie Peters")).toBeInTheDocument();
  });
});
