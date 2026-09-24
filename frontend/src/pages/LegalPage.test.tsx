import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { LegalPage } from "./LegalPage";

describe("LegalPage", () => {
  it("publishes the privacy policy and the narrow QuickBooks data boundary", () => {
    render(
      <MemoryRouter>
        <LegalPage document="privacy" />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Privacy Policy", level: 1 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "3. QuickBooks Online connection" })).toBeInTheDocument();
    expect(screen.getByText(/only to retrieve and verify the connected company's CompanyInfo/i)).toBeInTheDocument();
    expect(screen.getByText(/does not sell personal information/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "End-User Licence Terms" })).toHaveAttribute("href", "/legal/terms");
  });

  it("publishes internal-use licence terms without expanding QuickBooks permissions", () => {
    render(
      <MemoryRouter>
        <LegalPage document="terms" />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "End-User Licence Terms", level: 1 })).toBeInTheDocument();
    expect(screen.getByText(/limited, revocable, non-exclusive, non-transferable right/i)).toBeInTheDocument();
    expect(screen.getByText(/retrieves CompanyInfo solely to verify the selected company/i)).toBeInTheDocument();
    expect(screen.getByText(/does not create, update, delete, email, import, export, or synchronise/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Privacy Policy" })).toHaveAttribute("href", "/legal/privacy");
  });
});
