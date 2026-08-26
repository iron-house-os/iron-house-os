import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AppLayout } from "./AppLayout";

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { display_name: "Operations User", role: "operations_manager" },
    portalRole: "management",
    logout: vi.fn(),
  }),
}));

describe("AppLayout Help access", () => {
  it("keeps Help one tap away and carries the current page and project", () => {
    render(
      <MemoryRouter initialEntries={["/estimating?projectId=job-1&projectName=Bennett"]}>
        <AppLayout><div>Current page</div></AppLayout>
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "Open Help Centre" })).toHaveAttribute(
      "href",
      "/help?from=%2Festimating&projectId=job-1&projectName=Bennett",
    );
  });
});
