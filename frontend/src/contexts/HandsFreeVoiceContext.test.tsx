import { act, render, screen, waitFor } from "@testing-library/react";
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

import { HandsFreeVoiceProvider, interpretVoiceTranscript } from "./HandsFreeVoiceContext";
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

  constructor() {
    MockSpeechRecognition.instances.push(this);
  }

  emit(transcript: string) {
    this.onresult?.({ results: [{ 0: { transcript } }] });
  }

  end() {
    this.onend?.();
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
    testState.role = "admin";
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
    vi.unstubAllGlobals();
  });

  it("sends a command spoken in the wake phrase and speaks the answer", async () => {
    const user = userEvent.setup();
    renderProvider();

    await user.click(screen.getByRole("button", { name: "Enable hands-free Hey Chat" }));
    expect(MockSpeechRecognition.instances).toHaveLength(1);
    expect(MockSpeechRecognition.instances[0].start).toHaveBeenCalledOnce();

    act(() => MockSpeechRecognition.instances[0].emit("Hey Chat, where are project costs?"));

    await waitFor(() => expect(testState.send).toHaveBeenCalledWith("where are project costs?", undefined));
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
});
