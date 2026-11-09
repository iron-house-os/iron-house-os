import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getPerformanceSnapshot, resetPerformanceObservabilityForTests } from "../observability/performance";
import { apiFetch } from "./client";

describe("apiFetch observability", () => {
  beforeEach(() => {
    resetPerformanceObservabilityForTests();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("records response timing and status class without retaining request content", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 503 })));

    await apiFetch("/api/v1/projects/private-project-id?token=secret");

    const snapshot = getPerformanceSnapshot();
    expect(snapshot.api.requests).toBe(1);
    expect(snapshot.api.failures).toBe(1);
    expect(JSON.stringify(snapshot)).not.toContain("private-project-id");
    expect(JSON.stringify(snapshot)).not.toContain("secret");
  });

  it("separates aborted requests from failures", async () => {
    const controller = new AbortController();
    controller.abort();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new DOMException("The operation was aborted.", "AbortError")),
    );

    await expect(apiFetch("/api/v1/iron-house-chat/messages", { signal: controller.signal })).rejects.toThrow();

    expect(getPerformanceSnapshot().api).toMatchObject({
      requests: 1,
      failures: 0,
      aborted: 1,
    });
  });
});
