import { describe, expect, it } from "vitest";

import { modules } from "./modules";

describe("Iron House OS frontend scaffold", () => {
  it("registers the dashboard module", () => {
    expect(modules.some((module) => module.path === "/dashboard")).toBe(true);
  });
});
