import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

describe("Project workspace coarse-pointer layout", () => {
  it("stacks the selected project before management controls on iPad-like pointers", () => {
    const styles = readFileSync(new URL("../styles.css", import.meta.url), "utf-8");

    expect(styles).toContain("@media (pointer: coarse)");
    expect(styles).toContain(".project-workspace-layout--selected");
    expect(styles).toContain("grid-template-columns: minmax(0, 1fr)");
    expect(styles).toContain(
      ".project-workspace-layout--selected .project-workspace-management",
    );
    expect(styles).toContain("order: 9999");
  });
});
