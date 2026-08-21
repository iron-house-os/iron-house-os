import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { FormReviewPanel } from "./FormReviewPanel";

describe("FormReviewPanel", () => {
  beforeEach(() => {
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:preview"),
      revokeObjectURL: vi.fn(),
    });
  });

  it("preserves valid falsey review values", () => {
    render(<FormReviewPanel
      title="Daily record"
      destination="Project 100 / Field forms"
      items={[
        { label: "Quantity", value: 0 },
        { label: "Issue present", value: false },
        { label: "Notes", value: "" },
      ]}
      files={[]}
      onFilesChange={vi.fn()}
      category="job_photo"
      onBack={vi.fn()}
      onPost={vi.fn()}
    />);

    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.getByText("No")).toBeInTheDocument();
    expect(screen.getByText("Not entered")).toBeInTheDocument();
  });

  it("locks photo selection and removal while posting", () => {
    const photo = new File(["photo"], "field-photo.jpg", { type: "image/jpeg" });
    render(<FormReviewPanel
      title="Daily record"
      destination="Project 100 / Field forms"
      items={[]}
      files={[photo]}
      onFilesChange={vi.fn()}
      category="job_photo"
      onBack={vi.fn()}
      onPost={vi.fn()}
      posting
    />);

    expect(screen.getByLabelText("Take photos or choose multiple")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Remove field-photo.jpg" })).toBeDisabled();
  });
});
