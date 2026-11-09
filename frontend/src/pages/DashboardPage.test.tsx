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
