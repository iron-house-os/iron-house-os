import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HelpCenterPage } from "./HelpCenterPage";

const auth = vi.hoisted(() => ({ role: "viewer" as "viewer" | "operations_manager", portalRole: "employee" as "employee" | "foreman" | "management" }));
const coachApi = vi.hoisted(() => ({ send: vi.fn() }));

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { role: auth.role },
    portalRole: auth.portalRole,
  }),
}));

vi.mock("../api/helpCoach", () => ({ helpCoachApi: coachApi }));

describe("Help Centre", () => {
  beforeEach(() => coachApi.send.mockReset());

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
});
