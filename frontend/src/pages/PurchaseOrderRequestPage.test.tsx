import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fieldOperationsApi } from "../api/fieldOperations";
import { PurchaseOrderRequestPage } from "./PurchaseOrderRequestPage";

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "admin-1", email: "admin@ironhousecontracting.com", role: "admin" },
    portalRole: "management",
  }),
}));

vi.mock("../api/fieldOperations", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/fieldOperations")>();
  return {
    ...actual,
    fieldOperationsApi: {
      ...actual.fieldOperationsApi,
      bootstrap: vi.fn(),
      createRecord: vi.fn(),
    },
  };
});

describe("PurchaseOrderRequestPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    window.history.replaceState({}, "", "/request-po?projectId=job-1&projectName=Linked+Job");
    vi.mocked(fieldOperationsApi.bootstrap).mockResolvedValue({
      projects: [{ id: "job-1", name: "Linked Job", project_number: "IH-2026-030" }],
      suppliers: [],
      cost_codes: [],
      records: [],
    } as never);
  });

  it("preselects the job carried from the guided workflow", async () => {
    render(<PurchaseOrderRequestPage />);

    expect(await screen.findByRole("combobox", { name: "Job" })).toHaveValue("job-1");
    expect(screen.getByRole("option", { name: "IH-2026-030 Linked Job" })).toBeInTheDocument();
  });
});
