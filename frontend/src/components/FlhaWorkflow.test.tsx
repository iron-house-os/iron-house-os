import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { FieldOperationsBootstrap } from "../api/fieldOperations";
import { FlhaWorkflow } from "./FlhaWorkflow";

vi.mock("./UniversalPhotoField", () => ({ UniversalPhotoField: () => <div data-testid="shared-photo-field" /> }));

const data = {
  projects: [{ id: "project-1", name: "River Road" }],
  employees: [
    { id: "foreman-1", first_name: "Alex", last_name: "Foreperson", email: "alex@example.com", portal_role: "foreman" },
    { id: "worker-1", first_name: "Sam", last_name: "Worker", email: "sam@example.com", portal_role: "employee" },
  ],
  records: [],
} as unknown as FieldOperationsBootstrap;

describe("FlhaWorkflow", () => {
  it("renders the complete mobile-first screening, hierarchy, emergency and shared-photo workflow", async () => {
    const user = userEvent.setup();
    render(<FlhaWorkflow data={data} onSaved={vi.fn()} onError={vi.fn()} />);

    expect(screen.getByRole("heading", { name: /plan, control and acknowledge/i })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "yes" })).toHaveLength(10);
    expect(screen.getByLabelText(/site \/ location/i)).toBeRequired();
    expect(screen.getByLabelText(/supervisor \/ foreperson/i)).toHaveValue("Alex Foreperson");
    expect(screen.getByLabelText(/control hierarchy/i)).toHaveValue("engineering");
    expect(screen.getByLabelText(/muster point/i)).toBeRequired();
    expect(screen.getByLabelText(/stop-work triggers/i)).toBeRequired();
    expect(screen.getByTestId("shared-photo-field")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /excavation preset/i }));
    expect(screen.getByDisplayValue("Excavation and trench access")).toBeInTheDocument();
    expect(screen.getByText(/critical rows require an accepted control/i)).toBeInTheDocument();
  });
});
