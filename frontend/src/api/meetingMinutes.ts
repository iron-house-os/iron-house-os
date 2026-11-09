import { apiFetch } from "./client";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type MeetingActionItem = {
  task: string;
  owner: string | null;
  due_date: string | null;
};

export type MeetingMinutesStatus = {
  enabled: boolean;
  configured: boolean;
  transcription_model: string;
  summary_model: string;
  max_audio_bytes: number;
  audio_retained: false;
};

export type MeetingMinutesDraft = {
  transcript: string;
  summary: string;
  priority_points: string[];
  decisions: string[];
  action_items: MeetingActionItem[];
  transcription_model: string | null;
  summary_model: string;
  audio_retained: false;
};

export type MeetingMinute = {
  id: string;
  owner_account_id: string;
  project_id: string | null;
  title: string;
  meeting_date: string;
  attendees: string[];
  transcript: string;
  summary: string;
  priority_points: string[];
  decisions: string[];
  action_items: MeetingActionItem[];
  transcription_model: string | null;
  summary_model: string;
  audio_retained: false;
  status: "approved";
  consent_confirmed: true;
  review_confirmed: true;
  created_by_email: string;
  created_at: string;
  updated_at: string;
};

export type MeetingMinuteListItem = {
  id: string;
  project_id: string | null;
  title: string;
  meeting_date: string;
  status: "approved";
  audio_retained: false;
  created_by_email: string;
  created_at: string;
};

export type MeetingMinuteCreate = {
  title: string;
  project_id: string | null;
  meeting_date: string;
  attendees: string[];
  transcript: string;
  summary: string;
  priority_points: string[];
  decisions: string[];
  action_items: MeetingActionItem[];
  transcription_model: string | null;
  summary_model: string;
  consent_confirmed: boolean;
  review_confirmed: boolean;
};

async function read<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Meeting Minutes request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const meetingMinutesApi = {
  status: () =>
    apiFetch(`${API_BASE_URL}/meeting-minutes/status`).then(read<MeetingMinutesStatus>),
  list: () => apiFetch(`${API_BASE_URL}/meeting-minutes`).then(read<MeetingMinuteListItem[]>),
  draftFromAudio: (
    audio: Blob,
    filename: string,
    title: string,
    attendees: string,
  ) => {
    const body = new FormData();
    body.append("audio", audio, filename);
    body.append("title", title);
    body.append("attendees", attendees);
    body.append("consent_confirmed", "true");
    return apiFetch(`${API_BASE_URL}/meeting-minutes/draft-from-audio`, {
      method: "POST",
      body,
    }).then(read<MeetingMinutesDraft>);
  },
  draftFromTranscript: (transcript: string, title: string, attendees: string[]) =>
    apiFetch(`${API_BASE_URL}/meeting-minutes/draft-from-transcript`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        transcript,
        title,
        attendees,
        consent_confirmed: true,
      }),
    }).then(read<MeetingMinutesDraft>),
  save: (payload: MeetingMinuteCreate) =>
    apiFetch(`${API_BASE_URL}/meeting-minutes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(read<MeetingMinute>),
};
