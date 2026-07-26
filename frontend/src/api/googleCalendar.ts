import { apiFetch } from "./client";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type GoogleCalendarStatus = {
  enabled: boolean;
  configured: boolean;
  connected: boolean;
  status: string;
  required_scope: string;
  last_synced_at: string | null;
  last_error: string | null;
};

export type GoogleCalendarEvent = {
  id: string;
  title: string;
  description: string | null;
  location: string | null;
  start: string;
  end: string;
  html_link: string | null;
  status: string;
  project_id: string | null;
};

export type GoogleCalendarEventCreate = {
  title: string;
  description: string | null;
  location: string | null;
  start: string;
  end: string;
  project_id: string | null;
  confirmed: boolean;
};

async function read<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Google Calendar request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const googleCalendarApi = {
  status: () =>
    apiFetch(`${API_BASE_URL}/google-calendar/status`).then(read<GoogleCalendarStatus>),
  startOAuth: () =>
    apiFetch(`${API_BASE_URL}/google-calendar/oauth/start`, { method: "POST" }).then(
      read<{ authorization_url: string }>,
    ),
  events: () =>
    apiFetch(`${API_BASE_URL}/google-calendar/events`).then(read<GoogleCalendarEvent[]>),
  createEvent: (payload: GoogleCalendarEventCreate) =>
    apiFetch(`${API_BASE_URL}/google-calendar/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(read<GoogleCalendarEvent>),
  disconnect: () =>
    apiFetch(`${API_BASE_URL}/google-calendar/disconnect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirmed: true }),
    }).then(read<GoogleCalendarStatus>),
};
