import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HelpCenterPage } from "./HelpCenterPage";

const auth = vi.hoisted(() => ({ role: "viewer" as "viewer" | "operations_manager", portalRole: "employee" as "employee" | "foreman" | "management" }));
const coachApi = vi.hoisted(() => ({
  send: vi.fn(),
  submitFeedback: vi.fn(),
  listImprovements: vi.fn(),
  listImprovementEvidence: vi.fn(),
  updateImprovement: vi.fn(),
}));

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { role: auth.role },
    portalRole: auth.portalRole,
  }),
}));

vi.mock("../api/helpCoach", () => ({ helpCoachApi: coachApi }));

describe("Help Centre", () => {
  beforeEach(() => {
    coachApi.send.mockReset();
    coachApi.submitFeedback.mockReset();
    coachApi.listImprovements.mockReset();
    coachApi.listImprovementEvidence.mockReset();
    coachApi.updateImprovement.mockReset();
    coachApi.submitFeedback.mockResolvedValue({
      recorded: true,
      improvement_id: "improvement-1",
      status: "recorded",
      message: "Thank you. Management will review this Help feedback.",
    });
    coachApi.listImprovements.mockResolvedValue({ items: [], total: 0 });
    coachApi.listImprovementEvidence.mockResolvedValue({ items: [], total: 0 });
  });

  it("shows page-specific, employee-safe guidance", () => {
    auth.role = "viewer";
    auth.portalRole = "employee";
    render(
      <MemoryRouter initialEntries={["/help?from=/employee-portal/time&projectId=job-1&projectName=Bennett"]}>
        <HelpCenterPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "What do you need to do?" })).toBeInTheDocument();
    expect(screen.getByText("Help with the page you were on")).toBeInTheDocument();
    expect(screen.getAllByText("Enter my time").length).toBeGreaterThan(0);
    expect(screen.getByText("Active project: Bennett")).toBeInTheDocument();
    expect(screen.queryByText("Financial Control")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Improvement Inbox" })).not.toBeInTheDocument();
  });

  it("searches with everyday terms", () => {
    auth.role = "viewer";
    auth.portalRole = "employee";
    render(
      <MemoryRouter initialEntries={["/help"]}>
        <HelpCenterPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByRole("searchbox", { name: "What are you trying to do?" }), { target: { value: "FLHA" } });
    expect(screen.getByRole("heading", { name: "Search results" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Complete the daily FLHA" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Enter my time" })).not.toBeInTheDocument();
  });

  it("makes module guides available to management", () => {
    auth.role = "operations_manager";
    auth.portalRole = "management";
    render(
      <MemoryRouter initialEntries={["/help"]}>
        <HelpCenterPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Financial Control" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Customer Quotes" })).toBeInTheDocument();
  });

  it("asks the role-safe Help Coach and links its approved source", async () => {
    auth.role = "viewer";
    auth.portalRole = "employee";
    coachApi.send.mockResolvedValue({
      answer: "Open Time and choose the correct date and project.",
      status: "completed",
      audience: "employee",
      mode: "read-only",
      sources: [{ id: "employee-enter-time", title: "Enter my time", path: "/employee-portal/time" }],
    });
    render(
      <MemoryRouter initialEntries={["/help?from=/employee-portal/time&projectId=job-1&projectName=Bennett"]}>
        <HelpCenterPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("What do you need help with?"), {
      target: { value: "How do I enter my time?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask Coach" }));

    await waitFor(() => expect(coachApi.send).toHaveBeenCalledWith(
      "How do I enter my time?",
      { route: "/employee-portal/time", projectName: "Bennett" },
    ));
    expect(await screen.findByText("Open Time and choose the correct date and project.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Enter my time/ })).toHaveAttribute(
      "href",
      "/employee-portal/time",
    );
    expect(screen.getByText("Grounded Help Coach answer")).toBeInTheDocument();
  });

  it("keeps static Help usable when the Coach is unavailable", async () => {
    auth.role = "viewer";
    auth.portalRole = "employee";
    coachApi.send.mockResolvedValue({
      answer: "Open Schedule in your portal and find the correct date.",
      status: "static_fallback",
      audience: "employee",
      mode: "read-only",
      sources: [{ id: "employee-check-schedule", title: "Check my schedule", path: "/employee-portal/schedule" }],
    });
    render(
      <MemoryRouter initialEntries={["/help"]}>
        <HelpCenterPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("What do you need help with?"), {
      target: { value: "Where is my schedule?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask Coach" }));

    expect(await screen.findByText("Open Schedule in your portal and find the correct date.")).toBeInTheDocument();
    expect(screen.getByText("Approved built-in guidance")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Search Help" })).toBeInTheDocument();
  });

  it("records simple employee feedback without sending the original question", async () => {
    auth.role = "viewer";
    auth.portalRole = "employee";
    render(
      <MemoryRouter initialEntries={["/help?from=/employee-portal/time&projectId=job-1&projectName=Bennett"]}>
        <HelpCenterPage />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "This helped" }));

    await waitFor(() => expect(coachApi.submitFeedback).toHaveBeenCalledWith({
      feedbackType: "helpful",
      route: "/employee-portal/time",
      projectName: "Bennett",
      sourceIds: ["employee-enter-time"],
      note: "",
    }));
    expect(await screen.findByText("Thank you. Management will review this Help feedback.")).toBeInTheDocument();
    expect(coachApi.submitFeedback.mock.calls[0][0]).not.toHaveProperty("question");
  });

  it("shows the management-only Improvement Inbox and saves review status", async () => {
    auth.role = "operations_manager";
    auth.portalRole = "management";
    const improvement = {
      id: "improvement-1",
      feedback_type: "stuck",
      route: "/employee-portal/time",
      source_ids: ["employee-enter-time"],
      status: "new",
      evidence_count: 3,
      last_seen_at: "2026-08-26T12:00:00Z",
      latest_note: "The save step is hard to find.",
      latest_project_name: "Bennett",
      review_note: null,
      reviewed_by: null,
      reviewed_at: null,
    };
    coachApi.listImprovements.mockResolvedValue({ items: [improvement], total: 1 });
    coachApi.listImprovementEvidence.mockResolvedValue({
      items: [{
        id: "evidence-1",
        audience: "employee",
        project_name: "Bennett",
        note: "The save step is hard to find.",
        created_at: "2026-08-26T12:00:00Z",
      }],
      total: 1,
    });
    coachApi.updateImprovement.mockResolvedValue({
      ...improvement,
      status: "reviewing",
      review_note: "Check wording with the crew.",
    });
    render(
      <MemoryRouter initialEntries={["/help"]}>
        <HelpCenterPage />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Improvement Inbox" })).toBeInTheDocument();
    expect(screen.getByText("3 reports · /employee-portal/time")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show 3 individual reports" }));
    await waitFor(() => expect(coachApi.listImprovementEvidence).toHaveBeenCalledWith("improvement-1"));
    expect(await screen.findByLabelText("Individual Help feedback reports")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Review status"), { target: { value: "reviewing" } });
    fireEvent.change(screen.getByLabelText("Management note (optional)"), {
      target: { value: "Check wording with the crew." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save review" }));

    await waitFor(() => expect(coachApi.updateImprovement).toHaveBeenCalledWith(
      "improvement-1",
      "reviewing",
      "Check wording with the crew.",
    ));
  });
});
