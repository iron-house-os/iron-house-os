import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, useAuth } from "./AuthContext";

const currentUser = {
  id: "current-user",
  email: "current@ironhousecontracting.com",
  display_name: "Current User",
  role: "admin",
  is_active: true,
  password_reset_required: false,
  last_login_at: null,
  created_at: "2026-08-21T06:00:00Z",
  updated_at: "2026-08-21T06:00:00Z",
};

function Probe() {
  const { user, logout } = useAuth();
  return <button type="button" onClick={() => void logout()}>{user?.email ?? "Signed out"}</button>;
}

describe("AuthContext draft recovery isolation", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === "POST") return new Response(null, { status: 204 });
      return new Response(JSON.stringify({ authentication: "authenticated", user: currentUser }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }));
  });

  afterEach(() => vi.unstubAllGlobals());

  it("clears another user's device buffer on account change and clears the current buffer on logout", async () => {
    window.localStorage.setItem("ihos:draft-recovery-owner", "previous-user");
    window.localStorage.setItem("ihos:draft-recovery:previous-user:estimate", "private draft");

    const user = userEvent.setup();
    render(<AuthProvider><Probe /></AuthProvider>);

    expect(await screen.findByRole("button", { name: currentUser.email })).toBeInTheDocument();
    expect(window.localStorage.getItem("ihos:draft-recovery:previous-user:estimate")).toBeNull();
    expect(window.localStorage.getItem("ihos:draft-recovery-owner")).toBe(currentUser.id);

    window.localStorage.setItem("ihos:draft-recovery:current-user:estimate", "current private draft");
    await user.click(screen.getByRole("button", { name: currentUser.email }));

    await waitFor(() => expect(screen.getByRole("button", { name: "Signed out" })).toBeInTheDocument());
    expect(window.localStorage.getItem("ihos:draft-recovery:current-user:estimate")).toBeNull();
    expect(window.localStorage.getItem("ihos:draft-recovery-owner")).toBeNull();
  });
});
