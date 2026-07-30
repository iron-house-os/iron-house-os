import { Bot, LoaderCircle, Mic, MicOff, Volume2 } from "lucide-react";
import {
  PropsWithChildren,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useNavigate } from "react-router-dom";

import { ironHouseChatApi } from "../api/ironHouseChat";
import {
  observeVoiceCommand,
  observeVoiceFailure,
  observeVoiceRecognizerStart,
  observeVoiceRecognizerStop,
  observeVoiceRestartScheduled,
  setVoiceResource,
} from "../observability/performance";
import { resolveVoiceControl } from "../utils/voiceControls";
import { resolveVoiceNavigation } from "../utils/voiceNavigation";
import { useAuth } from "./AuthContext";

type SpeechRecognitionEventLike = {
  results: ArrayLike<{ 0: { transcript: string } }>;
};

type SpeechRecognitionErrorEventLike = {
  error?: string;
};

type SpeechRecognitionLike = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onend: (() => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  start: () => void;
  stop: () => void;
  abort?: () => void;
};

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

type SpeechWindow = typeof window & {
  SpeechRecognition?: SpeechRecognitionConstructor;
  webkitSpeechRecognition?: SpeechRecognitionConstructor;
};

type VoicePhase = "off" | "listening" | "awaiting-command" | "thinking" | "speaking" | "error";

type VoiceInterpretation =
  | { kind: "ignore" }
  | { kind: "wake" }
  | { kind: "command"; command: string };

type HandsFreeVoiceContextValue = {
  enabled: boolean;
  phase: VoicePhase;
  speakAssistantResponse: (text: string) => void;
};

const HandsFreeVoiceContext = createContext<HandsFreeVoiceContextValue | null>(null);
const DEFAULT_RESTART_DELAY_MS = 250;
const APPLE_RESTART_DELAY_MS = 700;
const MIN_SPEECH_WATCHDOG_MS = 5000;
const MAX_SPEECH_WATCHDOG_MS = 30000;
const MAX_RESTART_DELAY_MS = 4000;
const MAX_CONSECUTIVE_RESTART_FAILURES = 5;

export function isHandsFreeVoiceFeatureEnabled(value = import.meta.env.VITE_HEY_CHAT_VOICE_ENABLED): boolean {
  return ["true", "1", "on", "yes"].includes(value?.trim().toLowerCase() ?? "");
}

export function interpretVoiceTranscript(transcript: string, awaitingCommand: boolean): VoiceInterpretation {
  const clean = transcript.trim();
  if (!clean) return { kind: "ignore" };

  const wakeMatch = clean.match(/^hey\s+chat\b[\s,.:;!?-]*(.*)$/i);
  if (wakeMatch) {
    const command = wakeMatch[1].trim();
    return command ? { kind: "command", command } : { kind: "wake" };
  }

  return awaitingCommand ? { kind: "command", command: clean } : { kind: "ignore" };
}

function recognitionConstructor(): SpeechRecognitionConstructor | undefined {
  const speechWindow = window as SpeechWindow;
  return speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
}

function isAppleTouchBrowser(): boolean {
  const platform = navigator.platform ?? "";
  const userAgent = navigator.userAgent ?? "";
  return /iPad|iPhone|iPod/i.test(userAgent) || (platform === "MacIntel" && navigator.maxTouchPoints > 1);
}

function detachRecognitionHandlers(recognition: SpeechRecognitionLike) {
  recognition.onend = null;
  recognition.onerror = null;
  recognition.onresult = null;
}

export function HandsFreeVoiceProvider({ children }: PropsWithChildren) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const appleTouchBrowser = useMemo(() => isAppleTouchBrowser(), []);
  const voiceFeatureEnabled = isHandsFreeVoiceFeatureEnabled();
  const allowed =
    voiceFeatureEnabled &&
    Boolean(user) &&
    !user?.password_reset_required &&
    (user?.role === "admin" || user?.role === "operations_manager");
  const [enabled, setEnabled] = useState(false);
  const [phase, setPhase] = useState<VoicePhase>("off");
  const [error, setError] = useState<string | null>(null);
  const enabledRef = useRef(false);
  const awaitingCommandRef = useRef(false);
  const busyRef = useRef(false);
  const pausedForSpeechRef = useRef(false);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const conversationIdRef = useRef<string | undefined>(undefined);
  const restartTimerRef = useRef<number | null>(null);
  const speechWatchdogTimerRef = useRef<number | null>(null);
  const activeUtteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const speechGenerationRef = useRef(0);
  const requestGenerationRef = useRef(0);
  const pendingRequestAbortRef = useRef<AbortController | null>(null);
  const restartFailureCountRef = useRef(0);
  const startRecognitionRef = useRef<() => void>(() => undefined);
  const handleTranscriptRef = useRef<(transcript: string) => void>(() => undefined);
  const lastSpokenRef = useRef<string | null>(null);

  const clearRestartTimer = useCallback(() => {
    if (restartTimerRef.current !== null) {
      window.clearTimeout(restartTimerRef.current);
      restartTimerRef.current = null;
      setVoiceResource("active_restart_timers", false);
    }
  }, []);

  const clearSpeechWatchdog = useCallback(() => {
    if (speechWatchdogTimerRef.current !== null) {
      window.clearTimeout(speechWatchdogTimerRef.current);
      speechWatchdogTimerRef.current = null;
      setVoiceResource("active_speech_watchdogs", false);
    }
  }, []);

  const cancelPendingRequest = useCallback(() => {
    requestGenerationRef.current += 1;
    pendingRequestAbortRef.current?.abort();
    pendingRequestAbortRef.current = null;
    setVoiceResource("active_requests", false);
  }, []);

  const cancelSpeech = useCallback(() => {
    speechGenerationRef.current += 1;
    clearSpeechWatchdog();
    const utterance = activeUtteranceRef.current;
    activeUtteranceRef.current = null;
    if (utterance) {
      utterance.onend = null;
      utterance.onerror = null;
    }
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  }, [clearSpeechWatchdog]);

  const scheduleRestart = useCallback((failure = false) => {
    clearRestartTimer();
    if (!enabledRef.current || pausedForSpeechRef.current) return;
    if (failure) {
      restartFailureCountRef.current += 1;
      if (restartFailureCountRef.current > MAX_CONSECUTIVE_RESTART_FAILURES) {
        enabledRef.current = false;
        setEnabled(false);
        setPhase("error");
        setError("Microphone listening stopped after repeated failures. Enable Hey Chat to try again.");
        observeVoiceFailure();
        return;
      }
    } else {
      restartFailureCountRef.current = 0;
    }
    const baseDelay = appleTouchBrowser ? APPLE_RESTART_DELAY_MS : DEFAULT_RESTART_DELAY_MS;
    const delay = failure
      ? Math.min(MAX_RESTART_DELAY_MS, baseDelay * 2 ** (restartFailureCountRef.current - 1))
      : baseDelay;
    observeVoiceRestartScheduled();
    setVoiceResource("active_restart_timers", true);
    restartTimerRef.current = window.setTimeout(() => {
      restartTimerRef.current = null;
      setVoiceResource("active_restart_timers", false);
      startRecognitionRef.current();
    }, delay);
  }, [appleTouchBrowser, clearRestartTimer]);

  const stopRecognition = useCallback(() => {
    const recognition = recognitionRef.current;
    recognitionRef.current = null;
    if (!recognition) return;
    observeVoiceRecognizerStop();
    detachRecognitionHandlers(recognition);
    try {
      if (recognition.abort) recognition.abort();
      else recognition.stop();
    } catch {
      // A browser may already have ended the recognition session.
    }
  }, []);

  const resumeListening = useCallback(
    (resumePhase: "listening" | "awaiting-command" = "listening") => {
      clearSpeechWatchdog();
      pausedForSpeechRef.current = false;
      if (!enabledRef.current) return;
      setPhase(resumePhase);
      scheduleRestart();
    },
    [clearSpeechWatchdog, scheduleRestart],
  );

  const speak = useCallback(
    (text: string, resumePhase: "listening" | "awaiting-command" = "listening") => {
      lastSpokenRef.current = text;
      if (!("speechSynthesis" in window) || typeof SpeechSynthesisUtterance === "undefined") {
        resumeListening(resumePhase);
        return;
      }

      clearRestartTimer();
      cancelSpeech();
      pausedForSpeechRef.current = true;
      stopRecognition();
      if (enabledRef.current) setPhase("speaking");

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "en-CA";
      const speechGeneration = speechGenerationRef.current;
      activeUtteranceRef.current = utterance;
      let completed = false;
      const finishSpeech = (watchdogExpired = false) => {
        if (
          completed ||
          speechGenerationRef.current !== speechGeneration ||
          activeUtteranceRef.current !== utterance
        ) {
          return;
        }
        completed = true;
        utterance.onend = null;
        utterance.onerror = null;
        activeUtteranceRef.current = null;
        clearSpeechWatchdog();
        if (watchdogExpired) window.speechSynthesis.cancel();
        resumeListening(resumePhase);
      };
      utterance.onend = () => finishSpeech();
      utterance.onerror = () => finishSpeech();
      const watchdogMs = Math.min(
        MAX_SPEECH_WATCHDOG_MS,
        Math.max(MIN_SPEECH_WATCHDOG_MS, text.length * 80),
      );
      speechWatchdogTimerRef.current = window.setTimeout(() => finishSpeech(true), watchdogMs);
      setVoiceResource("active_speech_watchdogs", true);
      window.speechSynthesis.speak(utterance);
    },
    [cancelSpeech, clearRestartTimer, clearSpeechWatchdog, resumeListening, stopRecognition],
  );

  const completeNavigation = useCallback(
    (path: string | number, label: string) => {
      awaitingCommandRef.current = false;
      setError(null);
      if (typeof path === "number") navigate(path);
      else navigate(path);

      if (appleTouchBrowser) {
        lastSpokenRef.current = `Opening ${label}.`;
        resumeListening();
      } else {
        speak(`Opening ${label}.`);
      }
    },
    [appleTouchBrowser, navigate, resumeListening, speak],
  );

  const submitVoiceCommand = useCallback(
    async (command: string) => {
      const clean = command.trim();
      if (!clean || busyRef.current) return;
      const commandStarted = performance.now();
      const completeCommandObservation = () => {
        observeVoiceCommand(performance.now() - commandStarted);
      };

      const control = resolveVoiceControl(clean);
      if (control) {
        awaitingCommandRef.current = false;
        setError(null);

        if (control === "back") {
          completeNavigation(-1, "the previous page");
          completeCommandObservation();
          return;
        }
        if (control === "home") {
          completeNavigation("/dashboard", "Dashboard");
          completeCommandObservation();
          return;
        }
        if (control === "help") {
          speak("You can ask a read-only question, open an OS module, go back, go home, repeat the last answer, or stop listening.");
          completeCommandObservation();
          return;
        }
        if (control === "repeat") {
          const previous = lastSpokenRef.current;
          speak(previous ?? "There is no previous response to repeat.");
          completeCommandObservation();
          return;
        }

        enabledRef.current = false;
        busyRef.current = false;
        pausedForSpeechRef.current = false;
        cancelPendingRequest();
        clearRestartTimer();
        cancelSpeech();
        stopRecognition();
        setEnabled(false);
        setPhase("off");
        if (!appleTouchBrowser) speak("Hey Chat is off.");
        completeCommandObservation();
        return;
      }

      const navigation = resolveVoiceNavigation(clean);
      if (navigation) {
        completeNavigation(navigation.path, navigation.label);
        completeCommandObservation();
        return;
      }

      busyRef.current = true;
      awaitingCommandRef.current = false;
      clearRestartTimer();
      pausedForSpeechRef.current = true;
      stopRecognition();
      setError(null);
      setPhase("thinking");
      const requestAbort = new AbortController();
      const requestGeneration = requestGenerationRef.current + 1;
      requestGenerationRef.current = requestGeneration;
      pendingRequestAbortRef.current = requestAbort;
      setVoiceResource("active_requests", true);

      try {
        const reply = await ironHouseChatApi.send(clean, conversationIdRef.current, requestAbort.signal);
        if (
          requestAbort.signal.aborted ||
          !enabledRef.current ||
          requestGenerationRef.current !== requestGeneration
        ) {
          return;
        }
        conversationIdRef.current = reply.conversation.id;
        if (reply.assistant_message.status === "completed") {
          speak(reply.assistant_message.content);
        } else {
          resumeListening();
        }
      } catch (reason) {
        if (requestAbort.signal.aborted || (reason instanceof DOMException && reason.name === "AbortError")) {
          return;
        }
        const message = reason instanceof Error ? reason.message : "Unable to reach Iron House Chat.";
        observeVoiceFailure();
        setError(message);
        speak("I couldn’t complete that request. Check Iron House Chat for details.");
      } finally {
        if (pendingRequestAbortRef.current === requestAbort) pendingRequestAbortRef.current = null;
        setVoiceResource("active_requests", false);
        if (requestGenerationRef.current === requestGeneration) busyRef.current = false;
        completeCommandObservation();
      }
    },
    [
      appleTouchBrowser,
      cancelPendingRequest,
      cancelSpeech,
      clearRestartTimer,
      completeNavigation,
      resumeListening,
      speak,
      stopRecognition,
    ],
  );

  const handleTranscript = useCallback(
    (transcript: string) => {
      if (!enabledRef.current || busyRef.current || pausedForSpeechRef.current) return;
      const interpretation = interpretVoiceTranscript(transcript, awaitingCommandRef.current);
      if (interpretation.kind === "ignore") return;
      if (interpretation.kind === "wake") {
        awaitingCommandRef.current = true;
        setError(null);
        if (appleTouchBrowser) {
          setPhase("awaiting-command");
          scheduleRestart();
        } else {
          speak("I’m listening.", "awaiting-command");
        }
        return;
      }
      void submitVoiceCommand(interpretation.command);
    },
    [appleTouchBrowser, scheduleRestart, speak, submitVoiceCommand],
  );
  handleTranscriptRef.current = handleTranscript;

  const startRecognition = useCallback(() => {
    if (!enabledRef.current || pausedForSpeechRef.current || recognitionRef.current) return;
    const Recognition = recognitionConstructor();
    if (!Recognition) {
      enabledRef.current = false;
      setEnabled(false);
      setPhase("error");
      setError("Voice recognition is not supported by this browser. Use a current Safari or Chrome device.");
      return;
    }

    const recognition = new Recognition();
    recognition.continuous = !appleTouchBrowser;
    recognition.interimResults = false;
    recognition.lang = "en-CA";
    recognition.onresult = (event) => {
      const result = event.results[event.results.length - 1];
      if (appleTouchBrowser && recognitionRef.current === recognition) {
        recognitionRef.current = null;
        observeVoiceRecognizerStop();
        detachRecognitionHandlers(recognition);
        try {
          if (recognition.abort) recognition.abort();
          else recognition.stop();
        } catch {
          // Safari may already be ending this single recognition session.
        }
      }
      restartFailureCountRef.current = 0;
      handleTranscriptRef.current(result[0].transcript);
      if (appleTouchBrowser && enabledRef.current && !pausedForSpeechRef.current) scheduleRestart();
    };
    recognition.onerror = (event) => {
      if (recognitionRef.current === recognition) {
        recognitionRef.current = null;
        observeVoiceRecognizerStop();
      }
      detachRecognitionHandlers(recognition);
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        observeVoiceFailure();
        enabledRef.current = false;
        setEnabled(false);
        setPhase("error");
        setError("Microphone permission was denied. Allow microphone access in the browser, then enable Hey Chat again.");
        return;
      }
      if (event.error !== "no-speech" && event.error !== "aborted") {
        observeVoiceFailure();
        setError("Microphone listening was interrupted. Hey Chat will retry while this tab remains open.");
      }
      if (enabledRef.current && !pausedForSpeechRef.current) scheduleRestart(true);
    };
    recognition.onend = () => {
      if (recognitionRef.current === recognition) {
        recognitionRef.current = null;
        observeVoiceRecognizerStop();
      }
      detachRecognitionHandlers(recognition);
      if (enabledRef.current && !pausedForSpeechRef.current) scheduleRestart(true);
    };
    recognitionRef.current = recognition;

    try {
      recognition.start();
      observeVoiceRecognizerStart();
      setError(null);
      setPhase(awaitingCommandRef.current ? "awaiting-command" : "listening");
    } catch {
      recognitionRef.current = null;
      detachRecognitionHandlers(recognition);
      observeVoiceFailure();
      setError("Unable to start microphone listening. Hey Chat will retry while this tab remains open.");
      scheduleRestart(true);
    }
  }, [appleTouchBrowser, scheduleRestart]);
  startRecognitionRef.current = startRecognition;

  const disable = useCallback(() => {
    enabledRef.current = false;
    awaitingCommandRef.current = false;
    busyRef.current = false;
    pausedForSpeechRef.current = false;
    restartFailureCountRef.current = 0;
    cancelPendingRequest();
    clearRestartTimer();
    cancelSpeech();
    stopRecognition();
    setEnabled(false);
    setPhase("off");
    setError(null);
  }, [cancelPendingRequest, cancelSpeech, clearRestartTimer, stopRecognition]);

  const enable = useCallback(() => {
    if (!allowed) return;
    if (!recognitionConstructor()) {
      setPhase("error");
      setError("Voice recognition is not supported by this browser. Use a current Safari or Chrome device.");
      return;
    }
    enabledRef.current = true;
    awaitingCommandRef.current = false;
    pausedForSpeechRef.current = false;
    restartFailureCountRef.current = 0;
    setEnabled(true);
    setError(null);
    setPhase("listening");
    startRecognitionRef.current();
  }, [allowed]);

  const speakAssistantResponse = useCallback(
    (text: string) => {
      if (enabledRef.current && voiceFeatureEnabled) speak(text);
    },
    [speak, voiceFeatureEnabled],
  );

  useEffect(() => {
    if (!allowed && enabledRef.current) disable();
  }, [allowed, disable]);

  useEffect(() => {
    const stopForBackground = () => {
      if (enabledRef.current) disable();
    };
    const handleVisibility = () => {
      if (document.visibilityState === "hidden") stopForBackground();
    };
    document.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener("pagehide", stopForBackground);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("pagehide", stopForBackground);
    };
  }, [disable]);

  useEffect(
    () => () => {
      enabledRef.current = false;
      cancelPendingRequest();
      clearRestartTimer();
      cancelSpeech();
      stopRecognition();
    },
    [cancelPendingRequest, cancelSpeech, clearRestartTimer, stopRecognition],
  );

  const value = useMemo(
    () => ({ enabled, phase, speakAssistantResponse }),
    [enabled, phase, speakAssistantResponse],
  );

  return (
    <HandsFreeVoiceContext.Provider value={value}>
      {children}
      {allowed ? (
        <HandsFreeVoiceControl
          enabled={enabled}
          error={error}
          phase={phase}
          supported={Boolean(recognitionConstructor())}
          onDisable={disable}
          onEnable={enable}
        />
      ) : null}
    </HandsFreeVoiceContext.Provider>
  );
}

export function useHandsFreeVoice(): HandsFreeVoiceContextValue {
  const context = useContext(HandsFreeVoiceContext);
  if (context === null) throw new Error("useHandsFreeVoice must be used within HandsFreeVoiceProvider.");
  return context;
}

function HandsFreeVoiceControl({
  enabled,
  error,
  phase,
  supported,
  onDisable,
  onEnable,
}: {
  enabled: boolean;
  error: string | null;
  phase: VoicePhase;
  supported: boolean;
  onDisable: () => void;
  onEnable: () => void;
}) {
  if (!enabled) {
    return (
      <div className="fixed bottom-4 right-4 z-40 max-w-[calc(100vw-2rem)] text-right">
        <button
          type="button"
          onClick={onEnable}
          disabled={!supported}
          className="inline-flex items-center gap-2 rounded-md bg-brand-gold px-4 py-3 text-sm font-semibold text-brand-black shadow-brand transition hover:bg-amber-400 disabled:cursor-not-allowed disabled:bg-iron-300"
          aria-label="Enable hands-free Hey Chat"
        >
          <Mic className="h-4 w-4" aria-hidden="true" />
          {supported ? "Enable Hey Chat" : "Voice unavailable"}
        </button>
        {error ? (
          <div role="alert" className="mt-2 max-w-sm rounded-md border border-red-200 bg-white p-3 text-left text-xs text-red-700 shadow-md">
            {error}
          </div>
        ) : null}
      </div>
    );
  }

  const status =
    phase === "awaiting-command"
      ? "Listening for your question"
      : phase === "thinking"
        ? "Working on your request"
        : phase === "speaking"
          ? "Speaking the answer"
          : "Listening for ‘Hey Chat’";
  const StatusIcon = phase === "thinking" ? LoaderCircle : phase === "speaking" ? Volume2 : Bot;

  return (
    <section
      aria-label="Hands-free Hey Chat"
      className="fixed bottom-4 right-4 z-40 w-[min(22rem,calc(100vw-2rem))] rounded-md border border-brand-gold/40 bg-brand-black p-4 text-white shadow-brand"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <span className="relative mt-0.5">
            <StatusIcon className={`h-5 w-5 text-brand-gold ${phase === "thinking" ? "animate-spin" : ""}`} aria-hidden="true" />
            {phase === "listening" || phase === "awaiting-command" ? (
              <span className="absolute -right-1 -top-1 h-2 w-2 animate-pulse rounded-full bg-red-500" aria-hidden="true" />
            ) : null}
          </span>
          <div className="min-w-0">
            <div className="text-sm font-semibold text-brand-silver">Hey Chat is on</div>
            <div className="mt-1 text-xs text-iron-100" aria-live="polite">{status}</div>
          </div>
        </div>
        <button
          type="button"
          onClick={onDisable}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-white/20 px-2.5 py-1.5 text-xs font-semibold text-white transition hover:border-brand-gold hover:text-brand-gold"
          aria-label="Stop hands-free Hey Chat"
        >
          <MicOff className="h-3.5 w-3.5" aria-hidden="true" />
          Stop
        </button>
      </div>
      {error ? <div role="alert" className="mt-3 rounded-md bg-red-950/70 p-2 text-xs text-red-100">{error}</div> : null}
      <div className="mt-3 border-t border-white/10 pt-2 text-[11px] text-iron-300">
        Open tab only • Management only • Navigation and read-only answers
      </div>
    </section>
  );
}
