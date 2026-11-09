import {
  Bell,
  CalendarCheck2,
  CalendarDays,
  Clock3,
  ExternalLink,
  Link2,
  Link2Off,
  MapPin,
  Pencil,
  Plus,
  ShieldCheck,
  Trash2,
  Users,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { Navigate } from "react-router-dom";

import {
  GoogleCalendarEvent,
  GoogleCalendarStatus,
  googleCalendarApi,
} from "../api/googleCalendar";
import { Project, projectsApi } from "../api/projects";
import { useAuth } from "../contexts/AuthContext";

function localInput(value: Date) {
  const local = new Date(value);
  local.setMinutes(local.getMinutes() - local.getTimezoneOffset());
  return local.toISOString().slice(0, 16);
}

function initialTimes() {
  const start = new Date();
  start.setMinutes(0, 0, 0);
  start.setHours(start.getHours() + 1);
  return {
    start: localInput(start),
    end: localInput(new Date(start.getTime() + 60 * 60 * 1000)),
  };
}

function displayDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-CA", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function GoogleCalendarPage() {
  const { user } = useAuth();
  const [calendarStatus, setCalendarStatus] = useState<GoogleCalendarStatus | null>(null);
  const [events, setEvents] = useState<GoogleCalendarEvent[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [projectId, setProjectId] = useState("");
  const [attendees, setAttendees] = useState("");
  const [reminderMinutes, setReminderMinutes] = useState("30");
  const [sendInvitations, setSendInvitations] = useState(false);
  const [editingEventId, setEditingEventId] = useState<string | null>(null);
  const [conflicts, setConflicts] = useState<GoogleCalendarEvent[]>([]);
  const [conflictConfirmed, setConflictConfirmed] = useState(false);
  const defaults = useMemo(initialTimes, []);
  const [start, setStart] = useState(defaults.start);
  const [end, setEnd] = useState(defaults.end);
  const [eventConfirmed, setEventConfirmed] = useState(false);
  const [disconnectConfirmed, setDisconnectConfirmed] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [creating, setCreating] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [cancellingEventId, setCancellingEventId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const canManage = user?.role === "admin" || user?.role === "operations_manager";

  useEffect(() => {
    if (!canManage) return;
    const outcome = new URLSearchParams(window.location.search).get("google_calendar");
    if (outcome === "connected") setNotice("Google Calendar connected.");
    if (outcome === "denied") setError("Google Calendar permission was not granted.");
    if (outcome === "failed") setError("Google Calendar could not be connected. Try again.");
    Promise.all([googleCalendarApi.status(), projectsApi.list()])
      .then(async ([status, projectList]) => {
        setCalendarStatus(status);
        setProjects(projectList.items);
        if (status.connected) setEvents(await googleCalendarApi.events());
      })
      .catch((reason) =>
        setError(reason instanceof Error ? reason.message : "Unable to load Google Calendar"),
      );
  }, [canManage]);

  async function connect() {
    setConnecting(true);
    setError(null);
    try {
      const result = await googleCalendarApi.startOAuth();
      window.location.assign(result.authorization_url);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to start Google connection");
      setConnecting(false);
    }
  }

  async function createEvent(event: FormEvent) {
    event.preventDefault();
    if (!eventConfirmed || creating) return;
    setCreating(true);
    setError(null);
    setNotice(null);
    try {
      const startIso = new Date(start).toISOString();
      const endIso = new Date(end).toISOString();
      const conflictResult = await googleCalendarApi.conflicts(
        startIso,
        endIso,
        editingEventId ?? undefined,
      );
      if (conflictResult.has_conflicts && !conflictConfirmed) {
        setConflicts(conflictResult.conflicts);
        setError("Scheduling conflict found. Review and confirm the overlap before saving.");
        return;
      }
      const attendeeList = attendees
        .split(/[,\n;]/)
        .map((value) => value.trim().toLowerCase())
        .filter(Boolean);
      const payload = {
        title: title.trim(),
        description: description.trim() || null,
        location: location.trim() || null,
        start: startIso,
        end: endIso,
        project_id: projectId || null,
        attendees: attendeeList,
        reminder_minutes: reminderMinutes ? [Number(reminderMinutes)] : [],
        send_invitations: attendeeList.length > 0 && sendInvitations,
        confirmed: true,
      };
      const saved = editingEventId
        ? await googleCalendarApi.updateEvent(editingEventId, payload)
        : await googleCalendarApi.createEvent(payload);
      setEvents((current) =>
        [...current.filter((item) => item.id !== editingEventId), saved].sort(
          (left, right) => new Date(left.start).getTime() - new Date(right.start).getTime(),
        ),
      );
      const wasEditing = Boolean(editingEventId);
      resetEventForm();
      setNotice(
        wasEditing
          ? "Event updated. Confirmed attendee notifications were sent."
          : attendeeList.length
            ? "Event created and invitations sent to the confirmed attendees."
            : "Event created on your primary Google Calendar. No invitations were sent.",
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to create the calendar event");
    } finally {
      setCreating(false);
    }
  }

  function resetEventForm() {
    const next = initialTimes();
    setTitle("");
    setDescription("");
    setLocation("");
    setProjectId("");
    setAttendees("");
    setReminderMinutes("30");
    setSendInvitations(false);
    setStart(next.start);
    setEnd(next.end);
    setEditingEventId(null);
    setConflicts([]);
    setConflictConfirmed(false);
    setEventConfirmed(false);
  }

  function editEvent(calendarEvent: GoogleCalendarEvent) {
    setEditingEventId(calendarEvent.id);
    setTitle(calendarEvent.title);
    setDescription(calendarEvent.description ?? "");
    setLocation(calendarEvent.location ?? "");
    setProjectId(calendarEvent.project_id ?? "");
    setAttendees(calendarEvent.attendees.join(", "));
    setReminderMinutes(String(calendarEvent.reminder_minutes[0] ?? 30));
    setSendInvitations(calendarEvent.attendees.length > 0);
    setStart(localInput(new Date(calendarEvent.start)));
    setEnd(localInput(new Date(calendarEvent.end)));
    setConflicts([]);
    setConflictConfirmed(false);
    setEventConfirmed(false);
    setError(null);
    setNotice("Review the event changes before saving.");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function cancelEvent(calendarEvent: GoogleCalendarEvent) {
    if (
      !window.confirm(
        `Cancel “${calendarEvent.title}”? Confirmed attendees will be notified.`,
      )
    ) {
      return;
    }
    setCancellingEventId(calendarEvent.id);
    setError(null);
    try {
      await googleCalendarApi.cancelEvent(calendarEvent.id, true);
      setEvents((current) => current.filter((item) => item.id !== calendarEvent.id));
      if (editingEventId === calendarEvent.id) resetEventForm();
      setNotice("Event cancelled and attendee updates sent.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to cancel the event");
    } finally {
      setCancellingEventId(null);
    }
  }

  async function disconnect() {
    if (!disconnectConfirmed || disconnecting) return;
    setDisconnecting(true);
    setError(null);
    try {
      const nextStatus = await googleCalendarApi.disconnect();
      setCalendarStatus(nextStatus);
      setEvents([]);
      setDisconnectConfirmed(false);
      setNotice("Google Calendar disconnected and stored tokens cleared.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to disconnect Google Calendar");
    } finally {
      setDisconnecting(false);
    }
  }

  if (!canManage) return <Navigate to="/dashboard" replace />;

  return (
    <section className="space-y-6">
      <div className="border-b border-iron-100 pb-6">
        <div className="flex items-center gap-3">
          <CalendarDays className="h-8 w-8 text-brand-gold" />
          <h1 className="text-3xl font-semibold text-iron-950">Google Calendar</h1>
        </div>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
          View your next 90 days and deliberately add Iron House events to your primary calendar.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatusCard
          label="Connection"
          value={
            calendarStatus?.connected
              ? "Connected"
              : calendarStatus?.configured
                ? "Ready to connect"
                : "Configuration required"
          }
        />
        <StatusCard label="Permission" value="Owned events only" />
        <StatusCard label="Operations" value="Invites, changes & conflicts" />
      </div>

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

      {!calendarStatus?.configured && calendarStatus ? (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm leading-6 text-amber-900">
          <strong>Google Cloud setup required.</strong> Enable the Calendar API, create an Internal web
          OAuth client, and add the production redirect URI. Client secrets and tokens remain server-side.
        </div>
      ) : null}

      {!calendarStatus?.connected ? (
        <div className="rounded-md border border-iron-100 bg-white p-5 shadow-sm">
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 h-5 w-5 text-brand-gold" />
            <div>
              <h2 className="font-semibold text-iron-950">Connect your calendar</h2>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-iron-500">
                Iron House requests permission to read and manage events only on calendars you own. It
                does not request calendar-sharing administration.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => void connect()}
            disabled={
              connecting ||
              !calendarStatus?.enabled ||
              !calendarStatus?.configured
            }
            className="mt-4 inline-flex items-center gap-2 rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white disabled:bg-iron-300"
          >
            <Link2 className="h-4 w-4" />
            {connecting ? "Opening Google…" : "Connect Google Calendar"}
          </button>
        </div>
      ) : (
        <>
          <form
            onSubmit={(event) => void createEvent(event)}
            className="rounded-md border border-iron-100 bg-white p-5 shadow-sm"
          >
            <div className="flex items-start gap-3">
              <Plus className="mt-0.5 h-5 w-5 text-brand-gold" />
              <div>
                <h2 className="font-semibold text-iron-950">
                  {editingEventId ? "Update calendar event" : "Create calendar event"}
                </h2>
                <p className="mt-1 text-sm text-iron-500">
                  Review the commitment before it is written to Google Calendar.
                </p>
              </div>
            </div>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <label className="text-sm font-medium text-iron-800 md:col-span-2">
                Event title
                <input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  required
                  maxLength={300}
                  className="mt-1 w-full rounded-md border border-iron-200 px-3 py-2"
                />
              </label>
              <label className="text-sm font-medium text-iron-800">
                Start
                <input
                  type="datetime-local"
                  value={start}
                  onChange={(event) => setStart(event.target.value)}
                  required
                  className="mt-1 w-full rounded-md border border-iron-200 px-3 py-2"
                />
              </label>
              <label className="text-sm font-medium text-iron-800">
                End
                <input
                  type="datetime-local"
                  value={end}
                  onChange={(event) => setEnd(event.target.value)}
                  required
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
                Location (optional)
                <input
                  value={location}
                  onChange={(event) => setLocation(event.target.value)}
                  maxLength={500}
                  className="mt-1 w-full rounded-md border border-iron-200 px-3 py-2"
                />
              </label>
              <label className="text-sm font-medium text-iron-800 md:col-span-2">
                Description (optional)
                <textarea
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  rows={4}
                  maxLength={5000}
                  className="mt-1 w-full resize-y rounded-md border border-iron-200 px-3 py-2"
                />
              </label>
              <label className="text-sm font-medium text-iron-800 md:col-span-2">
                Attendee emails (optional)
                <textarea
                  value={attendees}
                  onChange={(event) => {
                    setAttendees(event.target.value);
                    if (!event.target.value.trim()) setSendInvitations(false);
                  }}
                  rows={2}
                  placeholder="mac@ironhousecontracting.com"
                  className="mt-1 w-full resize-y rounded-md border border-iron-200 px-3 py-2"
                />
                <span className="mt-1 block text-xs font-normal text-iron-500">
                  Separate multiple addresses with commas. Recipients must be verified before sending.
                </span>
              </label>
              <label className="text-sm font-medium text-iron-800">
                Reminder
                <select
                  value={reminderMinutes}
                  onChange={(event) => setReminderMinutes(event.target.value)}
                  className="mt-1 w-full rounded-md border border-iron-200 px-3 py-2"
                >
                  <option value="">Google default</option>
                  <option value="10">10 minutes before</option>
                  <option value="30">30 minutes before</option>
                  <option value="60">1 hour before</option>
                  <option value="1440">1 day before</option>
                </select>
              </label>
              <label className="flex items-center gap-3 self-end rounded-md border border-iron-200 p-3 text-sm text-iron-800">
                <input
                  type="checkbox"
                  checked={sendInvitations}
                  disabled={!attendees.trim()}
                  onChange={(event) => setSendInvitations(event.target.checked)}
                  className="h-4 w-4"
                />
                Send invitations and change notices
              </label>
            </div>
            {conflicts.length ? (
              <div className="mt-4 rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
                <strong>Scheduling conflict:</strong>
                <ul className="mt-2 space-y-1">
                  {conflicts.map((item) => (
                    <li key={item.id}>
                      {item.title}: {displayDate(item.start)} – {displayDate(item.end)}
                    </li>
                  ))}
                </ul>
                <label className="mt-3 flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={conflictConfirmed}
                    onChange={(event) => setConflictConfirmed(event.target.checked)}
                    className="mt-0.5 h-4 w-4"
                  />
                  I reviewed the overlap and approve saving this event.
                </label>
              </div>
            ) : null}
            <label className="mt-4 flex items-start gap-3 rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
              <input
                type="checkbox"
                checked={eventConfirmed}
                onChange={(event) => setEventConfirmed(event.target.checked)}
                className="mt-0.5 h-4 w-4"
              />
              <span>
                <strong>Event details reviewed.</strong>{" "}
                {editingEventId ? "Save these changes" : "Create this event"} on my primary Google
                Calendar
                {attendees.trim() ? " and send the confirmed attendee notifications." : "."}
              </span>
            </label>
            <div className="mt-4 flex flex-wrap gap-3">
              <button
                type="submit"
                disabled={
                  creating ||
                  !eventConfirmed ||
                  (!!attendees.trim() && !sendInvitations) ||
                  (conflicts.length > 0 && !conflictConfirmed) ||
                  !title.trim() ||
                  !start ||
                  !end ||
                  new Date(end) <= new Date(start)
                }
                className="inline-flex items-center gap-2 rounded-md bg-iron-950 px-5 py-2.5 text-sm font-semibold text-white disabled:bg-iron-300"
              >
                <CalendarCheck2 className="h-4 w-4" />
                {creating ? "Saving…" : editingEventId ? "Save changes" : "Create event"}
              </button>
              {editingEventId ? (
                <button
                  type="button"
                  onClick={resetEventForm}
                  className="rounded-md border border-iron-300 px-4 py-2 text-sm font-semibold text-iron-700"
                >
                  Cancel editing
                </button>
              ) : null}
            </div>
          </form>

          <div className="rounded-md border border-iron-100 bg-white p-5 shadow-sm">
            <div className="flex items-start gap-3">
              <Clock3 className="mt-0.5 h-5 w-5 text-brand-gold" />
              <div>
                <h2 className="font-semibold text-iron-950">Upcoming events</h2>
                <p className="mt-1 text-sm text-iron-500">Your primary calendar for the next 90 days.</p>
              </div>
            </div>
            {events.length === 0 ? (
              <p className="mt-5 rounded-md bg-iron-50 p-4 text-sm text-iron-500">
                No upcoming events found.
              </p>
            ) : (
              <div className="mt-5 divide-y divide-iron-100">
                {events.map((event) => (
                  <article key={event.id} className="py-4 first:pt-0 last:pb-0">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <h3 className="font-semibold text-iron-950">{event.title}</h3>
                        <p className="mt-1 text-sm text-iron-600">
                          {displayDate(event.start)} – {displayDate(event.end)}
                        </p>
                        {event.location ? (
                          <p className="mt-1 flex items-center gap-1.5 text-sm text-iron-500">
                            <MapPin className="h-3.5 w-3.5" /> {event.location}
                          </p>
                        ) : null}
                        {event.attendees.length ? (
                          <p className="mt-1 flex items-center gap-1.5 text-sm text-iron-500">
                            <Users className="h-3.5 w-3.5" /> {event.attendees.length} attendee
                            {event.attendees.length === 1 ? "" : "s"}
                          </p>
                        ) : null}
                        {event.reminder_minutes.length ? (
                          <p className="mt-1 flex items-center gap-1.5 text-sm text-iron-500">
                            <Bell className="h-3.5 w-3.5" /> {event.reminder_minutes[0]} minute reminder
                          </p>
                        ) : null}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => editEvent(event)}
                          className="inline-flex items-center gap-1 rounded-md border border-iron-200 px-3 py-2 text-sm font-semibold text-iron-700"
                        >
                          <Pencil className="h-3.5 w-3.5" /> Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => void cancelEvent(event)}
                          disabled={cancellingEventId === event.id}
                          className="inline-flex items-center gap-1 rounded-md border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 disabled:text-iron-300"
                        >
                          <Trash2 className="h-3.5 w-3.5" />{" "}
                          {cancellingEventId === event.id ? "Cancelling…" : "Cancel"}
                        </button>
                        {event.html_link ? (
                          <a
                            href={event.html_link}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 px-2 py-2 text-sm font-semibold text-iron-700 underline"
                          >
                            Open in Google <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        ) : null}
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-md border border-iron-100 bg-white p-5">
            <div className="flex items-start gap-3">
              <Link2Off className="mt-0.5 h-5 w-5 text-iron-500" />
              <div>
                <h2 className="font-semibold text-iron-950">Disconnect Google Calendar</h2>
                <p className="mt-1 text-sm text-iron-500">
                  Revokes Google access and clears encrypted tokens from Iron House OS.
                </p>
              </div>
            </div>
            <label className="mt-4 flex items-start gap-3 text-sm text-iron-700">
              <input
                type="checkbox"
                checked={disconnectConfirmed}
                onChange={(event) => setDisconnectConfirmed(event.target.checked)}
                className="mt-0.5 h-4 w-4"
              />
              <span>I understand that calendar access will stop until I reconnect.</span>
            </label>
            <button
              type="button"
              onClick={() => void disconnect()}
              disabled={!disconnectConfirmed || disconnecting}
              className="mt-3 rounded-md border border-red-300 px-4 py-2 text-sm font-semibold text-red-700 disabled:border-iron-200 disabled:text-iron-300"
            >
              {disconnecting ? "Disconnecting…" : "Disconnect calendar"}
            </button>
          </div>
        </>
      )}

      <p className="text-xs leading-5 text-iron-500">
        Management-only. Build 241 requires confirmation for invitations, event changes, conflict
        overrides, cancellations, and external commitments.
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
