import { describe, expect, it } from "vitest";

import { legacyOperatorTarget } from "./App";
import { buildHelpPath } from "./components/AppLayout";
import { workforceEntryRole } from "./contexts/AuthContext";
import { modules } from "./modules";

describe("Iron House OS frontend scaffold", () => {
  it("runs the frontend test gate", () => {
    expect(true).toBe(true);
  });

  it("keeps only Employee and Foreman workforce entries and redirects legacy operator links", () => {
    expect(modules.some((module) => module.label === "Operator Portal")).toBe(false);
    expect(workforceEntryRole("operator")).toBe("employee");
    expect(legacyOperatorTarget()).toBe("/employee-portal/operator");
    expect(legacyOperatorTarget("inspections")).toBe("/employee-portal/operator/inspections");
    expect(legacyOperatorTarget("schedule")).toBe("/employee-portal/schedule");
  });

  it("opens Help with the current page and active project context", () => {
    expect(buildHelpPath("/estimating", "job-1", "Bennett Civil")).toBe(
      "/help?from=%2Festimating&projectId=job-1&projectName=Bennett+Civil",
    );
    expect(buildHelpPath("/help", null, null)).toBe("/help");
  });
});
