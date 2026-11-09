import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MeetingMinutesPage } from "./MeetingMinutesPage";

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

const draft = {
  transcript: "Jeremie confirmed Monday mobilization after traffic control approval.",
  summary: "The team confirmed the mobilization sequence.",
  priority_points: ["Traffic control approval is required before mobilization."],
  decisions: ["Keep the Monday mobilization date."],
  action_items: [
    { task: "Confirm traffic control approval.", owner: "Jeremie", due_date: "2026-07-27" },
  ],
  transcription_model: null,
  summary_model: "gpt-5.6-sol",
  audio_retained: false,
};

describe("MeetingMinutesPage", () => {
  const requests: Array<{ url: string; method: string; body: BodyInit | null | undefined }> = [];

  beforeEach(() => {
    requests.length = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      requests.push({ url, method, body: init?.body });
      if (url.endsWith("/meeting-minutes/status")) {
        return Response.json({
          enabled: true,
          configured: true,
          transcription_model: "gpt-4o-mini-transcribe",
          summary_model: "gpt-5.6-sol",
          max_audio_bytes: 25 * 1024 * 1024,
          audio_retained: false,
        });
      }
      if (url.endsWith("/projects")) {
        return Response.json({ items: [], total: 0 });
      }
      if (url.endsWith("/meeting-minutes/draft-from-transcript") && method === "POST") {
        return Response.json(draft);
      }
      if (url.endsWith("/meeting-minutes") && method === "POST") {
        return Response.json({
          ...draft,
          id: "11111111-1111-4111-8111-111111111111",
          owner_account_id: "00000000-0000-0000-0000-000000000001",
          project_id: null,
          title: "Operations meeting",
          meeting_date: "2026-07-25T19:00:00-07:00",
          attendees: [],
          status: "approved",
          consent_confirmed: true,
          review_confirmed: true,
          created_by_email: "admin@ironhousecontracting.com",
          created_at: "2026-07-25T19:00:00-07:00",
          updated_at: "2026-07-25T19:00:00-07:00",
        }, { status: 201 });
      }
      if (url.endsWith("/meeting-minutes")) {
        return Response.json([]);
      }
      throw new Error(`Unexpected request: ${method} ${url}`);
    }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("requires consent and management review before saving approved minutes", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <MeetingMinutesPage />
      </MemoryRouter>,
    );

    const transcript = await screen.findByPlaceholderText(
      "The transcript appears here after recording, or paste one here…",
    );
    const draftButton = screen.getByRole("button", { name: "Prepare / refresh AI draft" });
    expect(draftButton).toBeDisabled();

    await user.type(transcript, draft.transcript);
    await user.click(screen.getByRole("checkbox", { name: /Recording consent confirmed/ }));
    await user.click(draftButton);

    expect(
      await screen.findByRole("heading", { name: "AI draft — management review required" }),
    ).toBeInTheDocument();
    const saveButton = screen.getByRole("button", { name: "Save approved minutes" });
    expect(saveButton).toBeDisabled();

    await user.click(screen.getByRole("checkbox", { name: /Management review complete/ }));
    await user.click(saveButton);

    expect(await screen.findByText("Approved meeting minutes saved. The raw audio was not retained."))
      .toBeInTheDocument();
    await waitFor(() => {
      const saveRequest = requests.find(
        (item) => item.url.endsWith("/meeting-minutes") && item.method === "POST",
      );
      expect(saveRequest).toBeDefined();
      const body = JSON.parse(String(saveRequest?.body));
      expect(body.consent_confirmed).toBe(true);
      expect(body.review_confirmed).toBe(true);
      expect(body).not.toHaveProperty("audio");
    });
  });
});
