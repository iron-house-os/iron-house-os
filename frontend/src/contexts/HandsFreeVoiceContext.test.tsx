import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, useLocation } from "react-router-dom";

const testState = vi.hoisted(() => ({
  role: "admin",
  send: vi.fn(),
}));

vi.mock("./AuthContext", () => ({
  useAuth: () => ({
    user: {
      id: "00000000-0000-0000-0000-000000000001",
      email: "manager@ironhousecontracting.com",
      display_name: "Iron House Manager",
      role: testState.role,
      is_active: true,
      password_reset_required: false,
    },
  }),
}));

vi.mock("../api/ironHouseChat", () => ({
  ironHouseChatApi: {
    send: testState.send,
  },
}));

import {
  HandsFreeVoiceProvider,
  interpretVoiceTranscript,
  isHandsFreeVoiceFeatureEnabled,
} from "./HandsFreeVoiceContext";
import {
  getPerformanceSnapshot,
  resetPerformanceObservabilityForTests,
} from "../observability/performance";
import { resolveVoiceControl } from "../utils/voiceControls";
import { resolveVoiceNavigation } from "../utils/voiceNavigation";

type ResultHandler = ((event: { results: ArrayLike<{ 0: { transcript: string } }> }) => void) | null;

class MockSpeechRecognition {
  static instances: MockSpeechRecognition[] = [];

  continuous = false;
  interimResults = false;
  lang = "";
  onresult: ResultHandler = null;
  onend: (() => void) | null = null;
  onerror: ((event: { error?: string }) => void) | null = null;
  start = vi.fn();
  stop = vi.fn();
  abort = vi.fn();

  constructor() {
    MockSpeechRecognition.instances.push(this);
  }

  emit(transcript: string) {
    this.onresult?.({ results: [{ 0: { transcript } }] });
  }

  end() {
    this.onend?.();
  }

  fail(error: string) {
    this.onerror?.({ error });
  }
}

class MockSpeechSynthesisUtterance {
  lang = "";
  onend: (() => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(public text: string) {}
}

const spoken: string[] = [];

describe("interpretVoiceTranscript", () => {
  it("recognizes direct and two-step wake commands without reacting to ordinary speech", () => {
    expect(interpretVoiceTranscript("Hey Chat, where are project costs?", false)).toEqual({
      kind: "command",
      command: "where are project costs?",
    });
    expect(interpretVoiceTranscript("hey chat", false)).toEqual({ kind: "wake" });
    expect(interpretVoiceTranscript("Show me the safety page", true)).toEqual({
      kind: "command",
      command: "Show me the safety page",
    });
    expect(interpretVoiceTranscript("ordinary site conversation", false)).toEqual({ kind: "ignore" });
  });
});

describe("isHandsFreeVoiceFeatureEnabled", () => {
  it("fails closed and accepts only explicit enabled values", () => {
    expect(isHandsFreeVoiceFeatureEnabled(undefined)).toBe(false);
    expect(isHandsFreeVoiceFeatureEnabled("false")).toBe(false);
    expect(isHandsFreeVoiceFeatureEnabled("unexpected")).toBe(false);
    expect(isHandsFreeVoiceFeatureEnabled("true")).toBe(true);
    expect(isHandsFreeVoiceFeatureEnabled("1")).toBe(true);
  });
});

describe("resolveVoiceControl", () => {
  it("recognizes only the approved local hands-free controls", () => {
    expect(resolveVoiceControl("Go back")).toBe("back");
    expect(resolveVoiceControl("Go home")).toBe("home");
    expect(resolveVoiceControl("What can I say?")).toBe("help");
    expect(resolveVoiceControl("Say that again")).toBe("repeat");
    expect(resolveVoiceControl("Stop listening")).toBe("stop");
    expect(resolveVoiceControl("Delete the project")).toBeNull();
  });
});

describe("resolveVoiceNavigation", () => {
  it("accepts explicit navigation requests and rejects ordinary questions", () => {
    expect(resolveVoiceNavigation("Open financial control")).toEqual({
      label: "Financial Control",
      path: "/finance",
    });
    expect(resolveVoiceNavigation("Hey, what are the project costs?")).toBeNull();
    expect(resolveVoiceNavigation("Show me the safety page")).toEqual({
      label: "Safety Program",
      path: "/safety-program",
    });
  });
});

function LocationProbe() {
  return <div data-testid="location">{useLocation().pathname}</div>;
}

function renderProvider() {
  return render(
    <MemoryRouter initialEntries={["/dashboard"]}>
      <HandsFreeVoiceProvider>
        <div>OS workspace</div>
        <LocationProbe />
      </HandsFreeVoiceProvider>
    </MemoryRouter>,
  );
}

describe("HandsFreeVoiceProvider", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_HEY_CHAT_VOICE_ENABLED", "true");
    testState.role = "admin";
    resetPerformanceObservabilityForTests();
    testState.send.mockReset();
    testState.send.mockResolvedValue({
      conversation: { id: "conversation-1" },
      user_message: { id: "message-1", role: "user", content: "Where are project costs?", status: "completed" },
      assistant_message: {
        id: "message-2",
        role: "assistant",
        content: "Open Financial Control from the main navigation.",
        status: "completed",
      },
    });
    MockSpeechRecognition.instances = [];
    spoken.length = 0;
    vi.stubGlobal("webkitSpeechRecognition", MockSpeechRecognition);
    vi.stubGlobal("SpeechSynthesisUtterance", MockSpeechSynthesisUtterance);
    vi.stubGlobal("speechSynthesis", {
      cancel: vi.fn(),
      speak: vi.fn((utterance: MockSpeechSynthesisUtterance) => {
        spoken.push(utterance.text);
        queueMicrotask(() => utterance.onend?.());
      }),
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("sends a command spoken in the wake phrase and speaks the answer", async () => {
    const user = userEvent.setup();
    renderProvider();

    await user.click(screen.getByRole("button", { name: "Enable hands-free Hey Chat" }));
    expect(MockSpeechRecognition.instances).toHaveLength(1);
    expect(MockSpeechRecognition.instances[0].start).toHaveBeenCalledOnce();

    act(() => MockSpeechRecognition.instances[0].emit("Hey Chat, where are project costs?"));

    await waitFor(() =>
      expect(testState.send).toHaveBeenCalledWith(
        "where are project costs?",
        undefined,
        expect.any(AbortSignal),
      ),
    );
    await waitFor(() => expect(spoken).toContain("Open Financial Control from the main navigation."));
    expect(screen.getByRole("button", { name: "Stop hands-free Hey Chat" })).toBeInTheDocument();
  });

  it("accepts a navigation direction after a wake-only phrase and automatically resumes listening", async () => {
    const user = userEvent.setup();
    renderProvider();

    await user.click(screen.getByRole("button", { name: "Enable hands-free Hey Chat" }));
    act(() => MockSpeechRecognition.instances[0].emit("Hey Chat"));

    await waitFor(() => expect(spoken).toContain("I’m listening."));
    await waitFor(() => expect(MockSpeechRecognition.instances.length).toBeGreaterThan(1));
    expect(await screen.findByText("Listening for your question")).toBeInTheDocument();

    const resumedRecognition = MockSpeechRecognition.instances.at(-1);
    act(() => resumedRecognition?.emit("Show me the safety page"));

    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/safety-program"));
    expect(testState.send).not.toHaveBeenCalled();
    expect(spoken).toContain("Opening Safety Program.");
  });

  it("restarts an interrupted recognition session while enabled", async () => {
    const user = userEvent.setup();
    renderProvider();

    await user.click(screen.getByRole("button", { name: "Enable hands-free Hey Chat" }));
    act(() => MockSpeechRecognition.instances[0].end());

    await waitFor(() => expect(MockSpeechRecognition.instances.length).toBeGreaterThan(1));
    expect(MockSpeechRecognition.instances.at(-1)?.start).toHaveBeenCalledOnce();
  });

  it("does not expose the microphone control to non-management accounts", () => {
    testState.role = "viewer";
    renderProvider();

    expect(screen.queryByRole("button", { name: /Hey Chat/i })).not.toBeInTheDocument();
  });

  it("keeps the microphone and speech feature disabled unless the build flag is explicitly enabled", () => {
    vi.stubEnv("VITE_HEY_CHAT_VOICE_ENABLED", "false");
    renderProvider();

    expect(screen.queryByRole("button", { name: /Hey Chat/i })).not.toBeInTheDocument();
    expect(MockSpeechRecognition.instances).toHaveLength(0);
  });

  it("opens a requested OS module without sending the command to the AI", async () => {
    const user = userEvent.setup();
    renderProvider();

    await user.click(screen.getByRole("button", { name: "Enable hands-free Hey Chat" }));
    act(() => MockSpeechRecognition.instances[0].emit("Hey Chat, open financial control"));

    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/finance"));
    expect(testState.send).not.toHaveBeenCalled();
    expect(spoken).toContain("Opening Financial Control.");
  });

  it("repeats the previous answer locally without another API request", async () => {
    const user = userEvent.setup();
    renderProvider();

    await user.click(screen.getByRole("button", { name: "Enable hands-free Hey Chat" }));
    act(() => MockSpeechRecognition.instances[0].emit("Hey Chat, where are project costs?"));

    await waitFor(() => expect(spoken).toContain("Open Financial Control from the main navigation."));
    await waitFor(() => expect(MockSpeechRecognition.instances.length).toBeGreaterThan(1));
    const resumedRecognition = MockSpeechRecognition.instances.at(-1);
    act(() => resumedRecognition?.emit("Hey Chat, repeat that"));

    await waitFor(() =>
      expect(spoken.filter((text) => text === "Open Financial Control from the main navigation.")).toHaveLength(2),
    );
    expect(testState.send).toHaveBeenCalledOnce();
  });

  it("stops hands-free listening by voice without an API request", async () => {
    const user = userEvent.setup();
    renderProvider();

    await user.click(screen.getByRole("button", { name: "Enable hands-free Hey Chat" }));
    act(() => MockSpeechRecognition.instances[0].emit("Hey Chat, stop listening"));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Enable hands-free Hey Chat" })).toBeInTheDocument(),
    );
    expect(testState.send).not.toHaveBeenCalled();
    expect(spoken).toContain("Hey Chat is off.");
  });

  it("cycles ten sequential commands on iPad with one active recognition session and complete cleanup", () => {
    vi.useFakeTimers();
    const platform = vi.spyOn(window.navigator, "platform", "get").mockReturnValue("MacIntel");
    const touchPointsDescriptor = Object.getOwnPropertyDescriptor(window.navigator, "maxTouchPoints");
    Object.defineProperty(window.navigator, "maxTouchPoints", { configurable: true, value: 5 });
    const userAgent = vi.spyOn(window.navigator, "userAgent", "get").mockReturnValue(
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/605.1.15 Version/26.0 Mobile Safari/605.1.15",
    );
    const view = renderProvider();

    fireEvent.click(screen.getByRole("button", { name: "Enable hands-free Hey Chat" }));

    for (let commandNumber = 0; commandNumber < 10; commandNumber += 1) {
      const recognition = MockSpeechRecognition.instances.at(-1);
      expect(recognition).toBeDefined();
      expect(recognition?.continuous).toBe(false);
      expect(recognition?.start).toHaveBeenCalledOnce();

      act(() => recognition?.emit("Hey Chat, go home"));

      expect(recognition?.abort).toHaveBeenCalledOnce();
      expect(recognition?.onresult).toBeNull();
      expect(recognition?.onerror).toBeNull();
      expect(recognition?.onend).toBeNull();

      act(() => vi.advanceTimersByTime(700));
      expect(MockSpeechRecognition.instances).toHaveLength(commandNumber + 2);
    }

    expect(testState.send).not.toHaveBeenCalled();
    expect(screen.getByTestId("location")).toHaveTextContent("/dashboard");
    expect(vi.getTimerCount()).toBe(0);

    view.unmount();

    expect(MockSpeechRecognition.instances.at(-1)?.abort).toHaveBeenCalledOnce();
    expect(MockSpeechRecognition.instances.every((recognition) =>
      recognition.onresult === null && recognition.onerror === null && recognition.onend === null
    )).toBe(true);
    expect(vi.getTimerCount()).toBe(0);
    platform.mockRestore();
    if (touchPointsDescriptor) {
      Object.defineProperty(window.navigator, "maxTouchPoints", touchPointsDescriptor);
    } else {
      Reflect.deleteProperty(window.navigator, "maxTouchPoints");
    }
    userAgent.mockRestore();
  });

  it("aborts a pending voice request and ignores its late response after Stop", async () => {
    let resolveReply: ((value: Awaited<ReturnType<typeof testState.send>>) => void) | undefined;
    testState.send.mockReturnValue(new Promise((resolve) => {
      resolveReply = resolve;
    }));
    const user = userEvent.setup();
    renderProvider();

    await user.click(screen.getByRole("button", { name: "Enable hands-free Hey Chat" }));
    act(() => MockSpeechRecognition.instances[0].emit("Hey Chat, summarize project risks"));
    await waitFor(() => expect(testState.send).toHaveBeenCalledOnce());

    const signal = testState.send.mock.calls[0][2] as AbortSignal;
    await user.click(screen.getByRole("button", { name: "Stop hands-free Hey Chat" }));
    expect(signal.aborted).toBe(true);

    await act(async () => {
      resolveReply?.({
        conversation: { id: "conversation-late" },
        user_message: { id: "message-late-user", role: "user", content: "Late", status: "completed" },
        assistant_message: {
          id: "message-late-assistant",
          role: "assistant",
          content: "This late answer must not be spoken.",
          status: "completed",
        },
      });
      await Promise.resolve();
    });

    expect(spoken).not.toContain("This late answer must not be spoken.");
  });

  it("releases voice resources when the page moves to the background", () => {
    const view = renderProvider();
    fireEvent.click(screen.getByRole("button", { name: "Enable hands-free Hey Chat" }));
    expect(getPerformanceSnapshot().voice.resources.active_recognition_sessions).toBe(1);

    act(() => window.dispatchEvent(new PageTransitionEvent("pagehide")));

    expect(screen.getByRole("button", { name: "Enable hands-free Hey Chat" })).toBeInTheDocument();
    expect(MockSpeechRecognition.instances[0].abort).toHaveBeenCalledOnce();
    expect(getPerformanceSnapshot().voice.resources).toEqual({
      active_recognition_sessions: 0,
      active_restart_timers: 0,
      active_speech_watchdogs: 0,
      active_requests: 0,
    });
    view.unmount();
  });

  it("bounds repeated recognition retries and never exceeds one active session", () => {
    vi.useFakeTimers();
    renderProvider();
    fireEvent.click(screen.getByRole("button", { name: "Enable hands-free Hey Chat" }));

    const retryDelays = [250, 500, 1000, 2000, 4000];
    for (const delay of retryDelays) {
      act(() => MockSpeechRecognition.instances.at(-1)?.end());
      act(() => vi.advanceTimersByTime(delay));
    }
    act(() => MockSpeechRecognition.instances.at(-1)?.end());

    expect(screen.getByText(/stopped after repeated failures/i)).toBeInTheDocument();
    expect(vi.getTimerCount()).toBe(0);
    expect(getPerformanceSnapshot().voice.maximum_active_recognition_sessions).toBe(1);
    expect(getPerformanceSnapshot().voice.resources).toEqual({
      active_recognition_sessions: 0,
      active_restart_timers: 0,
      active_speech_watchdogs: 0,
      active_requests: 0,
    });
  });
});
