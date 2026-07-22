import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { EmployeePortalPage } from "./EmployeePortalPage";

describe("EmployeePortalPage", () => {
  it("presents separate linked workspaces instead of one long employee page", () => {
    render(<MemoryRouter><EmployeePortalPage /></MemoryRouter>);

    expect(screen.getByRole("heading", { name: "Employee Portal" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /my time/i })).toHaveAttribute("href", "/employee-portal/time");
    expect(screen.getByRole("link", { name: /safety and toolbox talks/i })).toHaveAttribute("href", "/employee-portal/safety");
    expect(screen.getByRole("link", { name: /small equipment inspections/i })).toHaveAttribute("href", "/employee-portal/small-equipment");
  });
});
