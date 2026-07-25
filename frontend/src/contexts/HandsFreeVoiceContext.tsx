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
const RESTART_DELAY_MS = 250;

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

export function HandsFreeVoiceProvider({ children }: PropsWithChildren) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const allowed =
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
  const startRecognitionRef = useRef<() => void>(() => undefined);
  const handleTranscriptRef = useRef<(transcript: string) => void>(() => undefined);

  const clearRestartTimer = useCallback(() => {
    if (restartTimerRef.current !== null) {
      window.clearTimeout(restartTimerRef.current);
      restartTimerRef.current = null;
    }
  }, []);

  const scheduleRestart = useCallback(() => {
    clearRestartTimer();
    if (!enabledRef.current || pausedForSpeechRef.current) return;
    restartTimerRef.current = window.setTimeout(() => {
      restartTimerRef.current = null;
      startRecognitionRef.current();
    }, RESTART_DELAY_MS);
  }, [clearRestartTimer]);

  const stopRecognition = useCallback(() => {
    const recognition = recognitionRef.current;
    recognitionRef.current = null;
    if (!recognition) return;
    recognition.onend = null;
    try {
      recognition.stop();
    } catch {
      // A browser may already have ended the recognition session.
    }
  }, []);

  const resumeListening = useCallback(
    (resumePhase: "listening" | "awaiting-command" = "listening") => {
      pausedForSpeechRef.current = false;
      if (!enabledRef.current) return;
      setPhase(resumePhase);
      scheduleRestart();
    },
    [scheduleRestart],
  );

  const speak = useCallback(
    (text: string, resumePhase: "listening" | "awaiting-command" = "listening") => {
      if (!("speechSynthesis" in window) || typeof SpeechSynthesisUtterance === "undefined") {
        resumeListening(resumePhase);
        return;
      }

      clearRestartTimer();
      pausedForSpeechRef.current = true;
      stopRecognition();
      if (enabledRef.current) setPhase("speaking");

      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "en-CA";
      utterance.onend = () => resumeListening(resumePhase);
      utterance.onerror = () => resumeListening(resumePhase);
      window.speechSynthesis.speak(utterance);
    },
    [clearRestartTimer, resumeListening, stopRecognition],
  );

  const submitVoiceCommand = useCallback(
    async (command: string) => {
      const clean = command.trim();
      if (!clean || busyRef.current) return;

      const navigation = resolveVoiceNavigation(clean);
      if (navigation) {
        awaitingCommandRef.current = false;
        setError(null);
        navigate(navigation.path);
        speak(`Opening ${navigation.label}.`);
        return;
      }

      busyRef.current = true;
      awaitingCommandRef.current = false;
      clearRestartTimer();
      pausedForSpeechRef.current = true;
      stopRecognition();
      setError(null);
      setPhase("thinking");

      try {
        const reply = await ironHouseChatApi.send(clean, conversationIdRef.current);
        conversationIdRef.current = reply.conversation.id;
        if (reply.assistant_message.status === "completed") {
          speak(reply.assistant_message.content);
        } else {
          resumeListening();
        }
      } catch (reason) {
        const message = reason instanceof Error ? reason.message : "Unable to reach Iron House Chat.";
        setError(message);
        speak("I couldn’t complete that request. Check Iron House Chat for details.");
      } finally {
        busyRef.current = false;
      }
    },
    [clearRestartTimer, navigate, resumeListening, speak, stopRecognition],
  );

  const handleTranscript = useCallback(
    (transcript: string) => {
      if (!enabledRef.current || busyRef.current || pausedForSpeechRef.current) return;
      const interpretation = interpretVoiceTranscript(transcript, awaitingCommandRef.current);
      if (interpretation.kind === "ignore") return;
      if (interpretation.kind === "wake") {
        awaitingCommandRef.current = true;
        setError(null);
        speak("I’m listening.", "awaiting-command");
        return;
      }
      void submitVoiceCommand(interpretation.command);
    },
    [speak, submitVoiceCommand],
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
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = "en-CA";
    recognition.onresult = (event) => {
      const result = event.results[event.results.length - 1];
      handleTranscriptRef.current(result[0].transcript);
    };
    recognition.onerror = (event) => {
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        enabledRef.current = false;
        setEnabled(false);
        setPhase("error");
        setError("Microphone permission was denied. Allow microphone access in the browser, then enable Hey Chat again.");
        return;
      }
      setError("Microphone listening was interrupted. Hey Chat will retry while this tab remains open.");
    };
    recognition.onend = () => {
      if (recognitionRef.current === recognition) recognitionRef.current = null;
      if (enabledRef.current && !pausedForSpeechRef.current) scheduleRestart();
    };
    recognitionRef.current = recognition;

    try {
      recognition.start();
      setError(null);
      setPhase(awaitingCommandRef.current ? "awaiting-command" : "listening");
    } catch {
      recognitionRef.current = null;
      setError("Unable to start microphone listening. Hey Chat will retry while this tab remains open.");
      scheduleRestart();
    }
  }, [scheduleRestart]);
  startRecognitionRef.current = startRecognition;

  const disable = useCallback(() => {
    enabledRef.current = false;
    awaitingCommandRef.current = false;
    busyRef.current = false;
    pausedForSpeechRef.current = false;
    clearRestartTimer();
    stopRecognition();
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    setEnabled(false);
    setPhase("off");
    setError(null);
  }, [clearRestartTimer, stopRecognition]);

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
    setEnabled(true);
    setError(null);
    setPhase("listening");
    startRecognitionRef.current();
  }, [allowed]);

  const speakAssistantResponse = useCallback((text: string) => speak(text), [speak]);

  useEffect(() => {
    if (!allowed && enabledRef.current) disable();
  }, [allowed, disable]);

  useEffect(
    () => () => {
      enabledRef.current = false;
      clearRestartTimer();
      stopRecognition();
      if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    },
    [clearRestartTimer, stopRecognition],
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
          : "Listening for “Hey Chat”";
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
