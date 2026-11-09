import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { StrictMode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Project, projectsApi } from "../api/projects";
import { rfqPackagesApi } from "../api/rfqPackages";
import { suppliersApi } from "../api/suppliers";
import { DashboardPage } from "./DashboardPage";

vi.mock("../api/projects", () => ({ projectsApi: { list: vi.fn() } }));
vi.mock("../api/rfqPackages", () => ({ rfqPackagesApi: { list: vi.fn() } }));
vi.mock("../api/suppliers", () => ({ suppliersApi: { list: vi.fn() } }));

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}
const projectList = (name: string) => ({
  items: [{ id: name, name, status: "construction" } as Project], total: 1,
});
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(projectsApi.list).mockResolvedValue(projectList("Real project"));
  vi.mocked(rfqPackagesApi.list).mockResolvedValue({ items: [], total: 0 });
  vi.mocked(suppliersApi.list).mockResolvedValue({ items: [], total: 0 });
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("dashboard loading", () => {
  it("shows projects while suppliers are still loading and prevents overlapping refresh", async () => {
    const suppliers = deferred<Awaited<ReturnType<typeof suppliersApi.list>>>();
    vi.mocked(suppliersApi.list).mockReturnValue(suppliers.promise);
    render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    expect(await screen.findByText("Real project")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Refresh" }) as HTMLButtonElement).disabled).toBe(true);
    await act(async () => { suppliers.resolve({ items: [], total: 0 }); });
    await waitFor(() => expect((screen.getByRole("button", { name: "Refresh" }) as HTMLButtonElement).disabled).toBe(false));
  });

  it("keeps successful projects available when another section fails", async () => {
    vi.mocked(suppliersApi.list).mockRejectedValue(new Error("unavailable"));
    render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    expect(await screen.findByText("Real project")).toBeTruthy();
    expect((await screen.findByRole("alert")).textContent).toContain("suppliers");
    await waitFor(() => expect((screen.getByRole("button", { name: "Refresh" }) as HTMLButtonElement).disabled).toBe(false));
  });

  it("unlocks Refresh after a stalled section and ignores its late response", async () => {
    vi.useFakeTimers();
    const stalledProjects = deferred<Awaited<ReturnType<typeof projectsApi.list>>>();
    vi.mocked(projectsApi.list).mockReturnValueOnce(stalledProjects.promise).mockResolvedValue(projectList("Retried project"));
    render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    await act(async () => { await Promise.resolve(); });
    const refresh = screen.getByRole("button", { name: "Refresh" }) as HTMLButtonElement;
    expect(refresh.disabled).toBe(true);

    await act(async () => { await vi.advanceTimersByTimeAsync(15_000); });
    expect(screen.getByRole("alert").textContent).toContain("projects");
    expect(refresh.disabled).toBe(false);
    await act(async () => { refresh.click(); });
    expect(screen.getByText("Retried project")).toBeTruthy();
    expect(refresh.disabled).toBe(false);

    await act(async () => { stalledProjects.resolve(projectList("Late project")); });
    expect(screen.queryByText("Late project")).toBeNull();
    expect(screen.getByText("Retried project")).toBeTruthy();
  });

  it("unlocks retry when a failed section and a never-resolving section occur together", async () => {
    vi.useFakeTimers();
    vi.mocked(suppliersApi.list).mockReturnValue(new Promise(() => {}));
    vi.mocked(rfqPackagesApi.list).mockRejectedValue(new Error("unavailable"));
    render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    await act(async () => { await Promise.resolve(); });
    expect(screen.getByText("Real project")).toBeTruthy();
    expect(screen.getByRole("alert").textContent).toContain("RFQs");
    await act(async () => { await vi.advanceTimersByTimeAsync(15_000); });
    expect(screen.getByRole("alert").textContent).toContain("suppliers");
    expect((screen.getByRole("button", { name: "Refresh" }) as HTMLButtonElement).disabled).toBe(false);
    expect(screen.getByText("Real project")).toBeTruthy();
  });

  it("aborts timed-out transport requests before retrying", async () => {
    vi.useFakeTimers();
    const signals: AbortSignal[] = [];
    vi.mocked(projectsApi.list).mockImplementation((_status, _deleted, signal) => {
      signals.push(signal!);
      return new Promise((_resolve, reject) => {
        signal!.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
      });
    });
    render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    await act(async () => { await Promise.resolve(); });
    expect(signals[0].aborted).toBe(false);
    await act(async () => { await vi.advanceTimersByTimeAsync(15_000); });
    expect(signals[0].aborted).toBe(true);
    await act(async () => { (screen.getByRole("button", { name: "Refresh" }) as HTMLButtonElement).click(); });
    expect(signals).toHaveLength(2);
    expect(signals[1].aborted).toBe(false);
    await act(async () => { await vi.advanceTimersByTimeAsync(15_000); });
    expect(signals.every((signal) => signal.aborted)).toBe(true);
  });

  it("aborts all pending section requests on unmount and clears timeout work", async () => {
    vi.useFakeTimers();
    vi.mocked(projectsApi.list).mockReturnValue(new Promise(() => {}));
    vi.mocked(suppliersApi.list).mockReturnValue(new Promise(() => {}));
    vi.mocked(rfqPackagesApi.list).mockReturnValue(new Promise(() => {}));
    const view = render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    const signals = [
      vi.mocked(projectsApi.list).mock.calls[0][2]!,
      vi.mocked(suppliersApi.list).mock.calls[0][1]!,
      vi.mocked(rfqPackagesApi.list).mock.calls[0][1]!,
    ];
    expect(signals.every((signal) => !signal.aborted)).toBe(true);
    await act(async () => { view.unmount(); });
    expect(signals.every((signal) => signal.aborted)).toBe(true);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("aborts superseded StrictMode requests without affecting the current refresh", async () => {
    const oldProjects = deferred<Awaited<ReturnType<typeof projectsApi.list>>>();
    vi.mocked(projectsApi.list).mockReturnValueOnce(oldProjects.promise).mockResolvedValue(projectList("Current project"));
    render(<StrictMode><MemoryRouter><DashboardPage /></MemoryRouter></StrictMode>);
    expect(await screen.findByText("Current project")).toBeTruthy();
    expect(vi.mocked(projectsApi.list).mock.calls[0][2]?.aborted).toBe(true);
    expect(vi.mocked(projectsApi.list).mock.calls[1][2]?.aborted).toBe(false);
  });

  it("ignores an older response after StrictMode restarts the effect", async () => {
    const oldProjects = deferred<Awaited<ReturnType<typeof projectsApi.list>>>();
    vi.mocked(projectsApi.list).mockReturnValueOnce(oldProjects.promise).mockResolvedValue(projectList("Current project"));
    render(<StrictMode><MemoryRouter><DashboardPage /></MemoryRouter></StrictMode>);
    expect(await screen.findByText("Current project")).toBeTruthy();
    await act(async () => { oldProjects.resolve(projectList("Stale project")); });
    expect(screen.queryByText("Stale project")).toBeNull();
    expect(screen.getByText("Current project")).toBeTruthy();
  });
});
