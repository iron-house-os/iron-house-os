import type { ProfilerOnRenderCallback } from "react";

const MAX_SAMPLES = 100;
const ENABLED_VALUES = new Set(["true", "1", "on", "yes"]);

type DurationSummary = {
  count: number;
  average_ms: number;
  max_ms: number;
  p95_ms: number;
};

export type PerformanceSnapshot = {
  api: {
    requests: number;
    failures: number;
    aborted: number;
    latency: DurationSummary;
  };
  renders: Record<string, {
    commits: number;
    slow_commits: number;
    duration: DurationSummary;
  }>;
};

type MutableRenderMetric = {
  commits: number;
  slowCommits: number;
  durations: number[];
};

const apiDurations: number[] = [];
const renderMetrics = new Map<string, MutableRenderMetric>();

let apiRequests = 0;
let apiFailures = 0;
let apiAborted = 0;

function explicitFlag(value: string | undefined): boolean {
  return ENABLED_VALUES.has(value?.trim().toLowerCase() ?? "");
}

export function isPerformanceObservabilityEnabled(
  value = import.meta.env.VITE_PERFORMANCE_OBSERVABILITY_ENABLED,
  development = import.meta.env.DEV,
): boolean {
  return development || explicitFlag(value);
}

function appendBounded(values: number[], value: number) {
  values.push(Math.max(0, value));
  if (values.length > MAX_SAMPLES) values.shift();
}

function summarize(values: number[]): DurationSummary {
  if (values.length === 0) return { count: 0, average_ms: 0, max_ms: 0, p95_ms: 0 };
  const sorted = [...values].sort((left, right) => left - right);
  const p95Index = Math.max(0, Math.ceil(sorted.length * 0.95) - 1);
  const total = values.reduce((sum, value) => sum + value, 0);
  return {
    count: values.length,
    average_ms: Number((total / values.length).toFixed(2)),
    max_ms: Number(Math.max(...values).toFixed(2)),
    p95_ms: Number(sorted[p95Index].toFixed(2)),
  };
}

export function observeApiRequest(
  durationMs: number,
  outcome: "success" | "failure" | "aborted",
) {
  if (!isPerformanceObservabilityEnabled()) return;
  apiRequests += 1;
  if (outcome === "failure") apiFailures += 1;
  if (outcome === "aborted") apiAborted += 1;
  appendBounded(apiDurations, durationMs);
}

export const observeCoreRender: ProfilerOnRenderCallback = (
  id,
  _phase,
  actualDuration,
) => {
  if (!isPerformanceObservabilityEnabled()) return;
  const metric = renderMetrics.get(id) ?? { commits: 0, slowCommits: 0, durations: [] };
  metric.commits += 1;
  if (actualDuration > 50) metric.slowCommits += 1;
  appendBounded(metric.durations, actualDuration);
  renderMetrics.set(id, metric);
};

export function getPerformanceSnapshot(): PerformanceSnapshot {
  return {
    api: {
      requests: apiRequests,
      failures: apiFailures,
      aborted: apiAborted,
      latency: summarize(apiDurations),
    },
    renders: Object.fromEntries(
      [...renderMetrics.entries()].map(([id, metric]) => [
        id,
        {
          commits: metric.commits,
          slow_commits: metric.slowCommits,
          duration: summarize(metric.durations),
        },
      ]),
    ),
  };
}

export function installPerformanceDebugHandle() {
  if (!isPerformanceObservabilityEnabled() || typeof window === "undefined") return;
  window.__IHOS_PERFORMANCE__ = Object.freeze({
    snapshot: getPerformanceSnapshot,
  });
}

export function resetPerformanceObservabilityForTests() {
  apiDurations.length = 0;
  renderMetrics.clear();
  apiRequests = 0;
  apiFailures = 0;
  apiAborted = 0;
}

declare global {
  interface Window {
    __IHOS_PERFORMANCE__?: Readonly<{
      snapshot: () => PerformanceSnapshot;
    }>;
  }
}
