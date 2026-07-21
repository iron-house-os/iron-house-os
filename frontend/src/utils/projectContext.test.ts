import { beforeEach, describe, expect, it } from "vitest";

import {
  modulePathWithProjectContext,
  readEffectiveProjectContext,
  storeActiveProject,
} from "./projectContext";

describe("active project context", () => {
  beforeEach(() => window.localStorage.clear());

  it("carries the active project across project-aware navigation tabs", () => {
    storeActiveProject({ id: "project-tfn", name: "TFN Path" });

    expect(readEffectiveProjectContext("")).toEqual({
      projectId: "project-tfn",
      projectName: "TFN Path",
    });
    expect(modulePathWithProjectContext("/estimating", readEffectiveProjectContext(""))).toBe(
      "/estimating?projectId=project-tfn&projectName=TFN+Path",
    );
    expect(modulePathWithProjectContext("/projects", readEffectiveProjectContext(""))).toBe(
      "/projects/project-tfn",
    );
  });

  it("prefers an explicit routed project over the stored project", () => {
    storeActiveProject({ id: "project-tfn", name: "TFN Path" });

    expect(readEffectiveProjectContext("?projectId=project-downes&projectName=Downes+Road")).toEqual({
      projectId: "project-downes",
      projectName: "Downes Road",
    });
  });
});
