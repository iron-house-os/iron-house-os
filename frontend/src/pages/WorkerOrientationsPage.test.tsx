import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { employeeOnboardingApi, orientationTopicCodes } from "../api/employeeOnboarding";
import { WorkerOrientationsPage } from "./WorkerOrientationsPage";

vi.mock("../api/employeeOnboarding", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/employeeOnboarding")>();
  return {
    ...original,
    employeeOnboardingApi: {
      list: vi.fn(),
      deploymentStatus: vi.fn(),
      createOrientation: vi.fn(),
    },
  };
});

const worker = {
  id: "worker-1",
  legal_first_name: "Test",
  legal_last_name: "Worker",
  category: "employee",
  position: "operator",
  status: "active",
  primary_location: "Yard",
};

describe("WorkerOrientationsPage", () => {
  beforeEach(() => {
    vi.mocked(employeeOnboardingApi.list).mockResolvedValue({ items: [worker], total: 1 });
    vi.mocked(employeeOnboardingApi.deploymentStatus).mockResolvedValue({
      status: "Blocked",
      blockers: ["Company orientation is required."],
      latest_company_orientation_id: null,
      latest_site_orientation_id: null,
    });
    vi.mocked(employeeOnboardingApi.createOrientation).mockResolvedValue({});
  });

  it("prepopulates every controlled topic as an individual completion choice", async () => {
    const user = userEvent.setup();
    render(<WorkerOrientationsPage />);

    await screen.findByRole("option", { name: "Test Worker" });
    expect(screen.getAllByRole("checkbox", { name: /completed$/i })).toHaveLength(
      orientationTopicCodes.length,
    );
    expect(screen.getByText("0 of 13 topics recorded")).toBeInTheDocument();
    expect(screen.queryByPlaceholderText("Evidence reviewed")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save immutable record" })).toBeDisabled();

    await user.click(screen.getByRole("checkbox", { name: "Supervisor Contact completed" }));
    expect(screen.getByText("1 of 13 topics recorded")).toBeInTheDocument();

    await user.click(
      screen.getByRole("checkbox", { name: "Supervisor Contact not applicable" }),
    );
    expect(
      screen.getByRole("textbox", { name: "Supervisor Contact not-applicable reason" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Supervisor Contact completed" })).toBeDisabled();
  });

  it("saves controlled evidence after all topics are checked", async () => {
    const user = userEvent.setup();
    render(<WorkerOrientationsPage />);

    await screen.findByRole("option", { name: "Test Worker" });
    await user.type(screen.getByRole("textbox", { name: "Instructor" }), "A. Instructor");
    await user.type(screen.getByRole("textbox", { name: "Supervisor" }), "S. Supervisor");
    await user.type(screen.getByRole("textbox", { name: "Document version" }), "2026-08");
    await user.selectOptions(screen.getByRole("combobox", { name: "Competency" }), "passed");

    for (const checkbox of screen.getAllByRole("checkbox", { name: /completed$/i })) {
      await user.click(checkbox);
    }
    await user.click(screen.getByRole("checkbox", { name: "PPE verified" }));
    await user.click(screen.getByRole("checkbox", { name: "Qualifications verified" }));
    await user.click(screen.getByRole("checkbox", { name: "Worker acknowledged" }));
    await user.click(screen.getByRole("button", { name: "Save immutable record" }));

    await waitFor(() => expect(employeeOnboardingApi.createOrientation).toHaveBeenCalledTimes(1));
    expect(employeeOnboardingApi.createOrientation).toHaveBeenCalledWith(
      "worker-1",
      expect.objectContaining({
        competency_result: "passed",
        ppe_verified: true,
        qualifications_verified: true,
        worker_acknowledged: true,
        topics: orientationTopicCodes.map((code) =>
          expect.objectContaining({
            code,
            applicability: "applicable",
            evidence: expect.stringMatching(/^Completed in the orientation checklist:/),
            not_applicable_basis: null,
          }),
        ),
      }),
    );
  });
});
