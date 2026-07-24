import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LegalControlCentrePage } from "./LegalControlCentrePage";

const dashboard = {
  enabled: true, configured: false, mode: "supervised_draft_only", matters: [],
  candidate_deadline_count: 0,
  specialists: [{ key: "contracts", name: "Construction Contracts Counsel Assistant", mandate: "Contract review." }],
  authorities: [{ id: "bc-builders-lien-act", title: "BC Builders Lien Act", url: "https://example.invalid/authority", status: "active", jurisdiction: "BC" }],
};

describe("LegalControlCentrePage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => dashboard }));
  });

  it("renders the supervised legal gate and controlled registers", async () => {
    render(<LegalControlCentrePage />);
    expect(screen.getByText("AI Legal Control Centre")).toBeInTheDocument();
    expect(screen.getByText(/Human approval gate/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Construction Contracts Counsel Assistant")).toBeInTheDocument());
    expect(screen.getByText("BC Builders Lien Act")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open matter" })).toBeInTheDocument();
  });
});
