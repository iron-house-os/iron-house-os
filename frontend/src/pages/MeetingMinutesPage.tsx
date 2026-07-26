import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  FileText,
  Mic,
  Save,
  Square,
  Users,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Navigate } from "react-router-dom";

import {
  MeetingMinutesDraft,
  MeetingMinutesStatus,
  meetingMinutesApi,
} from "../api/meetingMinutes";
import { Project, projectsApi } from "../api/projects";
import { useAuth } from "../contexts/AuthContext";

const MAX_RECORDING_SECONDS = 60 * 60;

function localMeetingDate() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}

function names(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatDuration(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function recordingFormat() {
  const formats = ["audio/webm;codecs=opus", "audio/mp4", "audio/webm"];
  return formats.find((format) => MediaRecorder.isTypeSupported?.(format)) ?? "";
}

export function MeetingMinutesPage() {
  const { user } = useAuth();
  const [serviceStatus, setServiceStatus] = useState<MeetingMinutesStatus | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [savedCount, setSavedCount] = useState(0);
  const [title, setTitle] = useState("Operations meeting");
  const [projectId, setProjectId] = useState("");
  const [meetingDate, setMeetingDate] = useState(localMeetingDate);
  const [attendees, setAttendees] = useState("");
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  const [reviewConfirmed, setReviewConfirmed] = useState(false);
  const [draft, setDraft] = useState<MeetingMinutesDraft | null>(null);
  const [manualTranscript, setManualTranscript] = useState("");
  const [recording, setRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [processing, setProcessing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const canManage = user?.role === "admin" || user?.role === "operations_manager";
  const microphoneAvailable =
    typeof navigator !== "undefined" &&
    Boolean(navigator.mediaDevices?.getUserMedia) &&
    typeof MediaRecorder !== "undefined";
  const draftReady = Boolean(draft?.summary.trim() && draft?.transcript.trim());

  useEffect(() => {
    if (!canManage) return;
    Promise.all([
      meetingMinutesApi.status(),
      projectsApi.list(),
      meetingMinutesApi.list(),
    ])
      .then(([status, projectList, saved]) => {
        setServiceStatus(status);
        setProjects(projectList.items);
        setSavedCount(saved.length);
      })
      .catch((reason) =>
        setError(reason instanceof Error ? reason.message : "Unable to load Meeting Minutes"),
      );
  }, [canManage]);

  useEffect(() => {
    if (!recording) return;
    const timer = window.setInterval(() => {
      setRecordingSeconds((current) => {
        if (current + 1 >= MAX_RECORDING_SECONDS) {
          recorderRef.current?.stop();
          return MAX_RECORDING_SECONDS;
        }
        return current + 1;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [recording]);

  useEffect(
    () => () => {
      if (recorderRef.current?.state === "recording") recorderRef.current.stop();
      streamRef.current?.getTracks().forEach((track) => track.stop());
    },
    [],
  );

  const attendeesList = useMemo(() => names(attendees), [attendees]);

  async function processAudio(blob: Blob, mimeType: string) {
    setProcessing(true);
    setError(null);
    setNotice("Recording stopped. Transcribing and preparing the draft…");
    try {
      const extension = mimeType.includes("mp4") ? "mp4" : "webm";
      const result = await meetingMinutesApi.draftFromAudio(
        blob,
        `meeting.${extension}`,
        title,
        attendees,
      );
      setDraft(result);
      setManualTranscript(result.transcript);
      setReviewConfirmed(false);
      setNotice("AI draft ready. Review every section before saving approved minutes.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to process the recording");
      setNotice(null);
    } finally {
      setProcessing(false);
    }
  }

  async function startRecording() {
    if (!consentConfirmed || recording || processing) return;
    setError(null);
    setNotice(null);
    setDraft(null);
    setReviewConfirmed(false);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = recordingFormat();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      streamRef.current = stream;
      recorderRef.current = recorder;
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onerror = () => {
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        recorderRef.current = null;
        setError("The browser reported a microphone recording error.");
        setRecording(false);
      };
      recorder.onstop = () => {
        const outputType = recorder.mimeType || mimeType || "audio/webm";
        const blob = new Blob(chunksRef.current, { type: outputType });
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        recorderRef.current = null;
        setRecording(false);
        if (blob.size > 0) void processAudio(blob, outputType);
        else setError("No audio was captured. Check the microphone and try again.");
      };
      recorder.start(1000);
      setRecordingSeconds(0);
      setRecording(true);
      setNotice("Recording is active and visible. Stop it when the meeting ends.");
    } catch (reason) {
      const denied = reason instanceof DOMException && reason.name === "NotAllowedError";
      setError(
        denied
          ? "Microphone permission was denied. Allow access in the browser, then try again."
          : "The microphone could not be started on this device.",
      );
    }
  }

  function stopRecording() {
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
  }

  async function draftFromTranscript() {
    const transcript = manualTranscript.trim();
    if (!transcript || !consentConfirmed || processing) return;
    setProcessing(true);
    setError(null);
    setNotice("Preparing a draft from the transcript…");
    try {
      const result = await meetingMinutesApi.draftFromTranscript(
        transcript,
        title,
        attendeesList,
      );
      setDraft(result);
      setReviewConfirmed(false);
      setNotice("AI draft ready. Review every section before saving approved minutes.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to prepare the draft");
      setNotice(null);
    } finally {
      setProcessing(false);
    }
  }

  async function saveMinutes() {
    if (!draft || !reviewConfirmed || saving) return;
    setSaving(true);
    setError(null);
    try {
      await meetingMinutesApi.save({
        title: title.trim(),
        project_id: projectId || null,
        meeting_date: new Date(meetingDate).toISOString(),
        attendees: attendeesList,
        transcript: draft.transcript,
        summary: draft.summary,
        priority_points: draft.priority_points,
        decisions: draft.decisions,
        action_items: draft.action_items,
        transcription_model: draft.transcription_model,
        summary_model: draft.summary_model,
        consent_confirmed: true,
        review_confirmed: true,
      });
      setSavedCount((current) => current + 1);
      setNotice("Approved meeting minutes saved. The raw audio was not retained.");
      setDraft(null);
      setManualTranscript("");
      setReviewConfirmed(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to save meeting minutes");
    } finally {
      setSaving(false);
    }
  }

  if (!canManage) return <Navigate to="/dashboard" replace />;

  return (
    <section className="space-y-6">
      <div className="border-b border-iron-100 pb-6">
        <div className="flex items-center gap-3">
          <Mic className="h-8 w-8 text-brand-gold" />
          <h1 className="text-3xl font-semibold text-iron-950">Meeting Minutes</h1>
        </div>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
          Record a management meeting, prepare an AI draft, and save approved minutes after review.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatusCard
          label="AI service"
          value={
            serviceStatus && !serviceStatus.enabled
              ? "Disabled"
              : serviceStatus?.configured
                ? "Connected"
                : "Credential required"
          }
        />
        <StatusCard label="Audio retention" value="Never retained" />
        <StatusCard label="Approved records" value={String(savedCount)} />
      </div>

      {serviceStatus && !serviceStatus.configured ? (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          <strong>Activation pending.</strong> The server-side OpenAI credential must be configured.
          No credential is stored in the browser.
        </div>
      ) : null}
      {error ? (
        <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {notice ? (
        <div role="status" className="rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
          {notice}
        </div>
      ) : null}

      <div className="rounded-md border border-iron-100 bg-white p-5 shadow-sm">
        <div className="flex items-start gap-3">
          <ClipboardCheck className="mt-0.5 h-5 w-5 text-brand-gold" />
          <div>
            <h2 className="font-semibold text-iron-950">Meeting record</h2>
            <p className="mt-1 text-sm text-iron-500">Identify the meeting before recording.</p>
          </div>
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <label className="text-sm font-medium text-iron-800">
            Meeting title
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              maxLength={200}
              className="mt-1 w-full rounded-md border border-iron-200 px-3 py-2"
            />
          </label>
          <label className="text-sm font-medium text-iron-800">
            Meeting date and time
            <input
              type="datetime-local"
              value={meetingDate}
              onChange={(event) => setMeetingDate(event.target.value)}
              className="mt-1 w-full rounded-md border border-iron-200 px-3 py-2"
            />
          </label>
          <label className="text-sm font-medium text-iron-800">
            Project (optional)
            <select
              value={projectId}
              onChange={(event) => setProjectId(event.target.value)}
              className="mt-1 w-full rounded-md border border-iron-200 px-3 py-2"
            >
              <option value="">Company / no linked project</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.project_number ? `${project.project_number} — ` : ""}
                  {project.name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm font-medium text-iron-800">
            <span className="flex items-center gap-2"><Users className="h-4 w-4" /> Attendees</span>
            <input
              value={attendees}
              onChange={(event) => setAttendees(event.target.value)}
              placeholder="Names separated by commas"
              className="mt-1 w-full rounded-md border border-iron-200 px-3 py-2"
            />
          </label>
        </div>
      </div>

      <div className={`rounded-md border p-5 shadow-sm ${recording ? "border-red-400 bg-red-50" : "border-iron-100 bg-white"}`}>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className={`h-3 w-3 rounded-full ${recording ? "animate-pulse bg-red-600" : "bg-iron-300"}`} />
              <h2 className="font-semibold text-iron-950">
                {recording ? `Recording ${formatDuration(recordingSeconds)}` : "Microphone recorder"}
              </h2>
            </div>
            <p className="mt-1 text-sm text-iron-500">
              Maximum one hour and 25 MB. Audio is discarded after transcription.
            </p>
          </div>
          {recording ? (
            <button
              type="button"
              onClick={stopRecording}
              className="inline-flex items-center gap-2 rounded-md bg-red-700 px-4 py-2 text-sm font-semibold text-white"
            >
              <Square className="h-4 w-4" /> Stop recording
            </button>
          ) : (
            <button
              type="button"
              onClick={() => void startRecording()}
              disabled={
                !consentConfirmed ||
                processing ||
                !microphoneAvailable ||
                !serviceStatus?.configured ||
                !serviceStatus.enabled
              }
              className="inline-flex items-center gap-2 rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white disabled:bg-iron-300"
            >
              <Mic className="h-4 w-4" /> Start recording
            </button>
          )}
        </div>
        <label className="mt-5 flex items-start gap-3 rounded-md border border-iron-200 bg-white p-4 text-sm text-iron-800">
          <input
            type="checkbox"
            checked={consentConfirmed}
            disabled={recording || processing}
            onChange={(event) => setConsentConfirmed(event.target.checked)}
            className="mt-0.5 h-4 w-4"
          />
          <span>
            <strong>Recording consent confirmed.</strong> I confirmed that everyone present knows this
            meeting is being recorded.
          </span>
        </label>
        {!microphoneAvailable ? (
          <p className="mt-3 text-sm text-amber-800">
            This browser does not support microphone recording. Paste a transcript below.
          </p>
        ) : null}
      </div>

      <div className="rounded-md border border-iron-100 bg-white p-5 shadow-sm">
        <div className="flex items-start gap-3">
          <FileText className="mt-0.5 h-5 w-5 text-brand-gold" />
          <div>
            <h2 className="font-semibold text-iron-950">Transcript and draft</h2>
            <p className="mt-1 text-sm text-iron-500">
              The transcript is editable. You can also paste one when microphone recording is unavailable.
            </p>
          </div>
        </div>
        <textarea
          value={draft?.transcript ?? manualTranscript}
          onChange={(event) => {
            setManualTranscript(event.target.value);
            setDraft((current) => current ? { ...current, transcript: event.target.value } : current);
          }}
          rows={10}
          maxLength={200000}
          placeholder="The transcript appears here after recording, or paste one here…"
          className="mt-4 w-full resize-y rounded-md border border-iron-200 px-3 py-2 text-sm leading-6"
        />
        <button
          type="button"
          onClick={() => void draftFromTranscript()}
          disabled={
            !consentConfirmed ||
            processing ||
            !(draft?.transcript ?? manualTranscript).trim() ||
            !serviceStatus?.configured ||
            !serviceStatus.enabled
          }
          className="mt-3 rounded-md border border-iron-300 px-4 py-2 text-sm font-semibold text-iron-800 disabled:text-iron-300"
        >
          {processing ? "Preparing draft…" : "Prepare / refresh AI draft"}
        </button>
      </div>

      {draft ? (
        <div className="space-y-5 rounded-md border border-brand-gold/40 bg-white p-5 shadow-sm">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 text-amber-600" />
            <div>
              <h2 className="font-semibold text-iron-950">AI draft — management review required</h2>
              <p className="mt-1 text-sm text-iron-500">
                Correct omissions or errors. Saving changes the record status to approved.
              </p>
            </div>
          </div>
          <DraftTextArea
            label="Summary"
            value={draft.summary}
            onChange={(value) => setDraft({ ...draft, summary: value })}
            rows={5}
          />
          <DraftTextArea
            label="Priority points (one per line)"
            value={draft.priority_points.join("\n")}
            onChange={(value) => setDraft({ ...draft, priority_points: value.split("\n").filter(Boolean) })}
            rows={6}
          />
          <DraftTextArea
            label="Decisions (one per line)"
            value={draft.decisions.join("\n")}
            onChange={(value) => setDraft({ ...draft, decisions: value.split("\n").filter(Boolean) })}
            rows={5}
          />
          <div>
            <h3 className="text-sm font-semibold text-iron-950">Action items</h3>
            {draft.action_items.length === 0 ? (
              <p className="mt-2 text-sm text-iron-500">No explicit action items identified.</p>
            ) : (
              <div className="mt-2 space-y-3">
                {draft.action_items.map((item, index) => (
                  <div key={`${index}-${item.task}`} className="grid gap-2 rounded-md bg-iron-50 p-3 md:grid-cols-[1fr_12rem_10rem]">
                    <input
                      aria-label={`Action item ${index + 1}`}
                      value={item.task}
                      onChange={(event) => setDraft({
                        ...draft,
                        action_items: draft.action_items.map((current, currentIndex) =>
                          currentIndex === index ? { ...current, task: event.target.value } : current,
                        ),
                      })}
                      className="rounded-md border border-iron-200 px-3 py-2 text-sm"
                    />
                    <input
                      aria-label={`Action item ${index + 1} owner`}
                      value={item.owner ?? ""}
                      placeholder="Owner not stated"
                      onChange={(event) => setDraft({
                        ...draft,
                        action_items: draft.action_items.map((current, currentIndex) =>
                          currentIndex === index ? { ...current, owner: event.target.value || null } : current,
                        ),
                      })}
                      className="rounded-md border border-iron-200 px-3 py-2 text-sm"
                    />
                    <input
                      aria-label={`Action item ${index + 1} due date`}
                      type="date"
                      value={item.due_date ?? ""}
                      onChange={(event) => setDraft({
                        ...draft,
                        action_items: draft.action_items.map((current, currentIndex) =>
                          currentIndex === index ? { ...current, due_date: event.target.value || null } : current,
                        ),
                      })}
                      className="rounded-md border border-iron-200 px-3 py-2 text-sm"
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
          <label className="flex items-start gap-3 rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
            <input
              type="checkbox"
              checked={reviewConfirmed}
              onChange={(event) => setReviewConfirmed(event.target.checked)}
              className="mt-0.5 h-4 w-4"
            />
            <span>
              <strong>Management review complete.</strong> I reviewed the transcript, summary, priority
              points, decisions, and action items and approve them as the meeting record.
            </span>
          </label>
          <button
            type="button"
            onClick={() => void saveMinutes()}
            disabled={!reviewConfirmed || !draftReady || saving || !title.trim() || !meetingDate}
            className="inline-flex items-center gap-2 rounded-md bg-iron-950 px-5 py-2.5 text-sm font-semibold text-white disabled:bg-iron-300"
          >
            {saving ? <CheckCircle2 className="h-4 w-4" /> : <Save className="h-4 w-4" />}
            {saving ? "Saving…" : "Save approved minutes"}
          </button>
        </div>
      ) : null}

      <p className="text-xs leading-5 text-iron-500">
        Management-only. Do not record without consent. Do not discuss passwords, API keys, SINs,
        banking, medical, or payroll information. AI output is a draft until reviewed and saved.
      </p>
    </section>
  );
}

function StatusCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-iron-100 bg-white p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-iron-500">{label}</div>
      <div className="mt-2 font-semibold text-iron-950">{value}</div>
    </div>
  );
}

function DraftTextArea({
  label,
  value,
  onChange,
  rows,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  rows: number;
}) {
  return (
    <label className="block text-sm font-semibold text-iron-950">
      {label}
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        rows={rows}
        className="mt-2 w-full resize-y rounded-md border border-iron-200 px-3 py-2 text-sm font-normal leading-6"
      />
    </label>
  );
}
