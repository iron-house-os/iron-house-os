import type { ProfilerOnRenderCallback } from "react";

const MAX_SAMPLES = 100;
const ENABLED_VALUES = new Set(["true", "1", "on", "yes"]);

type DurationSummary = {
  count: number;
  average_ms: number;
  max_ms: number;
  p95_ms: number;
};

type VoiceResources = {
  active_recognition_sessions: number;
  active_restart_timers: number;
  active_speech_watchdogs: number;
  active_requests: number;
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
  voice: {
    recognizer_starts: number;
    restarts_scheduled: number;
    commands: number;
    failures: number;
    maximum_active_recognition_sessions: number;
    command_latency: DurationSummary;
    resources: VoiceResources;
  };
};

type MutableRenderMetric = {
  commits: number;
  slowCommits: number;
  durations: number[];
};

const apiDurations: number[] = [];
const commandDurations: number[] = [];
const renderMetrics = new Map<string, MutableRenderMetric>();

let apiRequests = 0;
let apiFailures = 0;
let apiAborted = 0;
let recognizerStarts = 0;
let restartsScheduled = 0;
let voiceCommands = 0;
let voiceFailures = 0;
let maximumActiveRecognitionSessions = 0;
const resources: VoiceResources = {
  active_recognition_sessions: 0,
  active_restart_timers: 0,
  active_speech_watchdogs: 0,
  active_requests: 0,
};

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

export function observeVoiceRecognizerStart() {
  if (!isPerformanceObservabilityEnabled()) return;
  recognizerStarts += 1;
  resources.active_recognition_sessions += 1;
  maximumActiveRecognitionSessions = Math.max(
    maximumActiveRecognitionSessions,
    resources.active_recognition_sessions,
  );
}

export function observeVoiceRecognizerStop() {
  if (!isPerformanceObservabilityEnabled()) return;
  resources.active_recognition_sessions = Math.max(0, resources.active_recognition_sessions - 1);
}

export function observeVoiceRestartScheduled() {
  if (!isPerformanceObservabilityEnabled()) return;
  restartsScheduled += 1;
}

export function observeVoiceCommand(durationMs: number) {
  if (!isPerformanceObservabilityEnabled()) return;
  voiceCommands += 1;
  appendBounded(commandDurations, durationMs);
}

export function observeVoiceFailure() {
  if (!isPerformanceObservabilityEnabled()) return;
  voiceFailures += 1;
}

export function setVoiceResource(
  resource: Exclude<keyof VoiceResources, "active_recognition_sessions">,
  active: boolean,
) {
  if (!isPerformanceObservabilityEnabled()) return;
  resources[resource] = active ? 1 : 0;
}

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
    voice: {
      recognizer_starts: recognizerStarts,
      restarts_scheduled: restartsScheduled,
      commands: voiceCommands,
      failures: voiceFailures,
      maximum_active_recognition_sessions: maximumActiveRecognitionSessions,
      command_latency: summarize(commandDurations),
      resources: { ...resources },
    },
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
  commandDurations.length = 0;
  renderMetrics.clear();
  apiRequests = 0;
  apiFailures = 0;
  apiAborted = 0;
  recognizerStarts = 0;
  restartsScheduled = 0;
  voiceCommands = 0;
  voiceFailures = 0;
  maximumActiveRecognitionSessions = 0;
  resources.active_recognition_sessions = 0;
  resources.active_restart_timers = 0;
  resources.active_speech_watchdogs = 0;
  resources.active_requests = 0;
}

declare global {
  interface Window {
    __IHOS_PERFORMANCE__?: Readonly<{
      snapshot: () => PerformanceSnapshot;
    }>;
  }
}
