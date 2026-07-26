import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GoogleCalendarPage } from "./GoogleCalendarPage";

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({
    user: {
      id: "00000000-0000-0000-0000-000000000001",
      email: "admin@ironhousecontracting.com",
      display_name: "Test Administrator",
      role: "admin",
    },
  }),
}));

const existingEvent = {
  id: "event-1",
  title: "Tender close",
  description: null,
  location: "Surrey, BC",
  start: "2026-07-28T16:00:00Z",
  end: "2026-07-28T17:00:00Z",
  html_link: "https://calendar.google.com/calendar/event?eid=event-1",
  status: "confirmed",
  project_id: null,
};

describe("GoogleCalendarPage", () => {
  const requests: Array<{ url: string; method: string; body: BodyInit | null | undefined }> = [];

  beforeEach(() => {
    requests.length = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const method = init?.method ?? "GET";
        requests.push({ url, method, body: init?.body });
        if (url.endsWith("/google-calendar/status")) {
          return Response.json({
            enabled: true,
            configured: true,
            connected: true,
            status: "connected",
            required_scope: "https://www.googleapis.com/auth/calendar.events.owned",
            last_synced_at: null,
            last_error: null,
          });
        }
        if (url.endsWith("/projects")) {
          return Response.json({ items: [], total: 0 });
        }
        if (url.endsWith("/google-calendar/events") && method === "GET") {
          return Response.json([existingEvent]);
        }
        if (url.endsWith("/google-calendar/events") && method === "POST") {
          return Response.json(
            {
              ...existingEvent,
              id: "event-2",
              title: "Site coordination",
              location: null,
            },
            { status: 201 },
          );
        }
        throw new Error(`Unexpected request: ${method} ${url}`);
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows upcoming events and requires review before creating an event", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <GoogleCalendarPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Tender close")).toBeInTheDocument();
    expect(screen.getByText("Owned events only")).toBeInTheDocument();
    const createButton = screen.getByRole("button", { name: "Create event" });
    expect(createButton).toBeDisabled();

    await user.type(screen.getByLabelText("Event title"), "Site coordination");
    await user.click(screen.getByRole("checkbox", { name: /Event details reviewed/ }));
    await user.click(createButton);

    expect(
      await screen.findByText(
        "Event created on your primary Google Calendar. No invitations were sent.",
      ),
    ).toBeInTheDocument();
    await waitFor(() => {
      const request = requests.find(
        (item) => item.url.endsWith("/google-calendar/events") && item.method === "POST",
      );
      expect(request).toBeDefined();
      const body = JSON.parse(String(request?.body));
      expect(body.confirmed).toBe(true);
      expect(body).not.toHaveProperty("attendees");
    });
  });
});
