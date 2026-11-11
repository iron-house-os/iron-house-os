import { afterEach, describe, expect, it, vi } from "vitest";

import { apiFetch } from "./client";
import { projectsApi } from "./projects";
import { suppliersApi } from "./suppliers";
import { rfqPackagesApi } from "./rfqPackages";

vi.mock("./client", () => ({ apiFetch: vi.fn() }));
afterEach(() => { vi.resetAllMocks(); });

describe("dashboard list cancellation", () => {
  it("forwards AbortSignal through all three list helpers while preserving filters", async () => {
    vi.mocked(apiFetch).mockImplementation(async () =>
      new Response(JSON.stringify({ items: [], total: 0 }), { status: 200 }));
    const controller = new AbortController();
    await projectsApi.list("construction", true, controller.signal);
    await suppliersApi.list({ search: "pipe", category: "civil" }, controller.signal);
    await rfqPackagesApi.list("project 1", controller.signal);
    const calls = vi.mocked(apiFetch).mock.calls;
    expect(String(calls[0][0])).toContain("/projects?status=construction&include_deleted=true");
    expect(String(calls[1][0])).toContain("/suppliers?search=pipe&category=civil");
    expect(String(calls[2][0])).toContain("/rfqs?project_id=project%201");
    calls.forEach(([, options]) => expect(options?.signal).toBe(controller.signal));
  });

  it("propagates a transport abort instead of converting it to successful data", async () => {
    const controller = new AbortController();
    const aborted = new DOMException("Aborted", "AbortError");
    vi.mocked(apiFetch).mockRejectedValue(aborted);
    controller.abort();
    await expect(projectsApi.list(undefined, false, controller.signal)).rejects.toBe(aborted);
    await expect(suppliersApi.list({}, controller.signal)).rejects.toBe(aborted);
    await expect(rfqPackagesApi.list(undefined, controller.signal)).rejects.toBe(aborted);
  });
});
