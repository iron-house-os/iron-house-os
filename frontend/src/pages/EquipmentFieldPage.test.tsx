import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { equipmentApi } from "../api/equipment";
import { EquipmentFieldPage } from "./EquipmentFieldPage";

vi.mock("../api/equipment", () => ({ equipmentApi: { get: vi.fn() } }));

describe("EquipmentFieldPage", () => {
  beforeEach(() => {
    vi.mocked(equipmentApi.get).mockResolvedValue({
      id: "equipment-1", name: "20 t excavator", equipment_type: "Excavator", identifier: "EX-20",
      status: "available", hourly_rate: 195, safety_procedure_codes: ["SWP-003", "SWP-008"],
      created_at: "2026-08-18T00:00:00Z", updated_at: "2026-08-18T00:00:00Z",
    });
  });

  it("shows only management-assigned controlled procedure references", async () => {
    render(<MemoryRouter initialEntries={["/equipment/field/equipment-1"]}><Routes><Route path="/equipment/field/:equipmentId" element={<EquipmentFieldPage />} /></Routes></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "20 t excavator" })).toBeInTheDocument();
    expect(screen.getByText(/SWP-003 · Mobile Equipment and Spotters/)).toBeInTheDocument();
    expect(screen.getByText(/SWP-008 · Lifting, Rigging and Suspended Loads/)).toBeInTheDocument();
    expect(screen.queryByText(/Confined Space Entry/)).not.toBeInTheDocument();
  });
});
