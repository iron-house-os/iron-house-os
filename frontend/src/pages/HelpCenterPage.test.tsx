import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { HelpCenterPage } from "./HelpCenterPage";

const auth = vi.hoisted(() => ({ role: "viewer" as "viewer" | "operations_manager", portalRole: "employee" as "employee" | "foreman" | "management" }));

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { role: auth.role },
    portalRole: auth.portalRole,
  }),
}));

describe("Help Centre", () => {
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
});
