import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EmployeePortalPage } from "./EmployeePortalPage";

describe("EmployeePortalPage", () => {
  it("gives employees access to the controlled safety program", () => {
    render(<EmployeePortalPage />);

    expect(screen.getByRole("heading", { name: "Employee Portal" })).toBeInTheDocument();
    const safetyLink = screen.getByRole("link", { name: /open safety program/i });
    expect(safetyLink).toHaveAttribute(
      "href",
      "https://docs.google.com/document/d/1ApKQs4xIR8axW0lIaeqqATDVaZWs1jvSzaZwYK6wUNw/edit?usp=drivesdk",
    );
    expect(safetyLink).toHaveAttribute("target", "_blank");
    expect(screen.getByText(/revision 1.1 incorporates current british columbia/i)).toBeInTheDocument();
  });
});
