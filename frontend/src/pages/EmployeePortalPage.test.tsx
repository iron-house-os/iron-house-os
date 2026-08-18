import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { EmployeePortalPage, incidentWorkDate } from "./EmployeePortalPage";

describe("EmployeePortalPage", () => {
  it("presents separate linked workspaces instead of one long employee page", () => {
    render(<MemoryRouter><EmployeePortalPage /></MemoryRouter>);

    expect(screen.getByRole("heading", { name: "Employee Portal" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /my time/i })).toHaveAttribute("href", "/employee-portal/time");
    expect(screen.getByRole("link", { name: /safety and toolbox talks/i })).toHaveAttribute("href", "/employee-portal/safety");
    expect(screen.getByRole("link", { name: /small equipment inspections/i })).toHaveAttribute("href", "/employee-portal/small-equipment");
  });

  it("derives an incident work date from the captured occurrence time", () => {
    expect(incidentWorkDate("2026-08-11T06:45", "2026-08-18")).toBe("2026-08-11");
    expect(incidentWorkDate("", "2026-08-18")).toBe("2026-08-18");
    expect(incidentWorkDate("2026-02-30T06:45", "2026-08-18")).toBe("2026-08-18");
  });
});
