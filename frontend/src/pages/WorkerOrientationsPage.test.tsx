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
  preferred_name: null,
  personal_email: "test.worker@example.com",
  mobile_phone: null,
  category: "field_staff" as const,
  position: "equipment_operator",
  supervisor_id: null,
  employment_type: "full_time",
  start_date: "2026-08-20",
  status: "active" as const,
  completion_percent: 100,
  missing_items: [],
  primary_location: "Yard",
  onboarding_package: null,
  reviewer_id: null,
  correction_note: null,
  invitation_expires_at: null,
  invited_at: null,
  submitted_at: "2026-08-20T08:00:00Z",
  approved_at: "2026-08-20T09:00:00Z",
  activated_at: "2026-08-20T10:00:00Z",
  created_at: "2026-08-20T07:00:00Z",
  updated_at: "2026-08-20T10:00:00Z",
};

const readyWorker = {
  ...worker,
  id: "worker-2",
  legal_first_name: "Ready",
  legal_last_name: "Worker",
  personal_email: "ready.worker@example.com",
};

describe("WorkerOrientationsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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

  it("keeps workers visible and fails closed when deployment status cannot be verified", async () => {
    vi.mocked(employeeOnboardingApi.deploymentStatus).mockRejectedValue(
      new Error("Onboarding request failed."),
    );

    render(<WorkerOrientationsPage />);

    expect(await screen.findByRole("option", { name: "Test Worker" })).toBeInTheDocument();
    expect(await screen.findByText("Status unavailable")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Deployment evidence is unverified. This worker is not cleared for deployment.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("Required evidence is complete.")).not.toBeInTheDocument();
    expect(employeeOnboardingApi.deploymentStatus).toHaveBeenCalledTimes(2);
  });

  it("keeps a pending status check fail-closed without showing a false failure", async () => {
    vi.mocked(employeeOnboardingApi.deploymentStatus).mockImplementation(
      () => new Promise(() => undefined),
    );

    render(<WorkerOrientationsPage />);

    expect(await screen.findByText("Checking status")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Deployment evidence is being verified. This worker is not cleared for deployment.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("Required evidence is complete.")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry status" })).not.toBeInTheDocument();
  });

  it("preserves a verified worker status when another worker status fails", async () => {
    vi.mocked(employeeOnboardingApi.list).mockResolvedValue({
      items: [worker, readyWorker],
      total: 2,
    });
    vi.mocked(employeeOnboardingApi.deploymentStatus).mockImplementation(async (workerId) => {
      if (workerId === readyWorker.id) {
        return {
          status: "Ready",
          blockers: [],
          latest_company_orientation_id: "orientation-1",
          latest_site_orientation_id: null,
        };
      }
      throw new Error("Onboarding request failed.");
    });

    render(<WorkerOrientationsPage />);

    expect(await screen.findByRole("option", { name: "Test Worker" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Ready Worker" })).toBeInTheDocument();
    expect(await screen.findByText("Ready")).toBeInTheDocument();
    expect(screen.getByText("Status unavailable")).toBeInTheDocument();
    expect(screen.getByText("Required evidence is complete.")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Deployment evidence is unverified. This worker is not cleared for deployment.",
      ),
    ).toBeInTheDocument();
    expect(employeeOnboardingApi.deploymentStatus).toHaveBeenCalledTimes(3);
  });

  it("lets management retry an unavailable deployment status", async () => {
    const user = userEvent.setup();
    vi.mocked(employeeOnboardingApi.deploymentStatus)
      .mockRejectedValueOnce(new Error("Onboarding request failed."))
      .mockRejectedValueOnce(new Error("Onboarding request failed."))
      .mockResolvedValue({
        status: "Blocked",
        blockers: ["Company orientation is required."],
        latest_company_orientation_id: null,
        latest_site_orientation_id: null,
      });

    render(<WorkerOrientationsPage />);

    await user.click(await screen.findByRole("button", { name: "Retry status" }));

    expect(await screen.findByText("Company orientation is required.")).toBeInTheDocument();
    expect(screen.getByText("Blocked")).toBeInTheDocument();
    expect(screen.queryByText("Status unavailable")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry status" })).not.toBeInTheDocument();
  });
});
