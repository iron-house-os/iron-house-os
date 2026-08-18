import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { equipmentApi } from "../api/equipment";
import { EquipmentPage } from "./EquipmentPage";

vi.mock("../contexts/AuthContext", () => ({ useAuth: () => ({ user: { role: "operations_manager" } }) }));
vi.mock("../components/EquipmentRateLibraryPanel", () => ({ EquipmentRateLibraryPanel: () => null }));
vi.mock("../components/UniversalPhotoField", () => ({ UniversalPhotoField: () => null }));
vi.mock("../api/equipment", () => ({
  equipmentStatuses: ["available", "reserved", "in_use", "maintenance", "retired"],
  equipmentApi: { list: vi.fn(), create: vi.fn(), update: vi.fn() },
}));

const item = {
  id: "equipment-1", name: "20 t excavator", equipment_type: "Excavator", identifier: "EX-20",
  status: "available" as const, hourly_rate: 195, safety_procedure_codes: [],
  created_at: "2026-08-18T00:00:00Z", updated_at: "2026-08-18T00:00:00Z",
};

describe("EquipmentPage safety field access", () => {
  beforeEach(() => {
    vi.mocked(equipmentApi.list).mockResolvedValue({
      items: [{ ...item, safety_procedure_codes: undefined as unknown as string[] }],
      total: 1,
    });
    vi.mocked(equipmentApi.update).mockResolvedValue({ ...item, safety_procedure_codes: ["SWP-003"] });
  });

  it("saves management assignments and generates a token-free QR field link", async () => {
    const user = userEvent.setup();
    render(<EquipmentPage />);
    expect(await screen.findByText("20 t excavator")).toBeInTheDocument();

    await user.click(screen.getByText("Manage field procedure assignments"));
    await user.click(screen.getByLabelText(/SWP-003 · Mobile Equipment and Spotters/));
    await user.click(screen.getByRole("button", { name: "Save procedure assignments" }));
    expect(equipmentApi.update).toHaveBeenCalledWith("equipment-1", { safety_procedure_codes: ["SWP-003"] });

    await user.click(screen.getByText("Equipment QR field link"));
    expect(await screen.findByRole("img", { name: "QR field link for EX-20" })).toHaveAttribute("src", expect.stringMatching(/^data:image\/svg\+xml/));
    expect(screen.getByText(/no password, token, rate, or safety record content/i)).toBeInTheDocument();
  });
});
