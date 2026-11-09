import { beforeEach, describe, expect, it } from "vitest";

import {
  getPerformanceSnapshot,
  installPerformanceDebugHandle,
  isPerformanceObservabilityEnabled,
  observeApiRequest,
  observeCoreRender,
  resetPerformanceObservabilityForTests,
} from "./performance";

describe("performance observability", () => {
  beforeEach(() => {
    resetPerformanceObservabilityForTests();
    Reflect.deleteProperty(window, "__IHOS_PERFORMANCE__");
  });

  it("fails closed outside development unless explicitly enabled", () => {
    expect(isPerformanceObservabilityEnabled(undefined, false)).toBe(false);
    expect(isPerformanceObservabilityEnabled("false", false)).toBe(false);
    expect(isPerformanceObservabilityEnabled("true", false)).toBe(true);
    expect(isPerformanceObservabilityEnabled(undefined, true)).toBe(true);
  });

  it("records only aggregate API and render lifecycle data", () => {
    observeApiRequest(100, "success");
    observeApiRequest(300, "failure");
    observeApiRequest(50, "aborted");
    observeCoreRender("core-modules", "mount", 60, 70, 1, 2);

    const snapshot = getPerformanceSnapshot();
    expect(snapshot.api).toEqual({
      requests: 3,
      failures: 1,
      aborted: 1,
      latency: { count: 3, average_ms: 150, max_ms: 300, p95_ms: 300 },
    });
    expect(snapshot.renders["core-modules"]).toMatchObject({
      commits: 1,
      slow_commits: 1,
    });
    expect(JSON.stringify(snapshot)).not.toContain("transcript");
    expect(JSON.stringify(snapshot)).not.toContain("credential");
    expect(JSON.stringify(snapshot)).not.toContain("project");
  });

  it("exposes a read-only snapshot handle in development", () => {
    observeApiRequest(25, "success");
    installPerformanceDebugHandle();

    expect(window.__IHOS_PERFORMANCE__?.snapshot().api.requests).toBe(1);
    expect(Object.isFrozen(window.__IHOS_PERFORMANCE__)).toBe(true);
  });

});
