import { useState } from "react";

import {
  documentAuditApi,
  DocumentAuditEventList,
  DocumentAuditFilters,
  DocumentAuditSummary,
} from "../api/documentAudit";

export function DocumentAuditPanel() {
  const [events, setEvents] = useState<DocumentAuditEventList | null>(null);
  const [summary, setSummary] = useState<DocumentAuditSummary | null>(null);
  const [action, setAction] = useState("");
  const [outcome, setOutcome] = useState("");
  const [actor, setActor] = useState("");
  const [projectId, setProjectId] = useState("");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  function filters(): DocumentAuditFilters {
    return { limit: 50, action, outcome, actor, project_id: projectId };
  }

  async function loadEvents() {
    setIsLoading(true);
    setError(null);
    try {
      const currentFilters = filters();
      const [nextEvents, nextSummary] = await Promise.all([
        documentAuditApi.list(currentFilters),
        documentAuditApi.summary(currentFilters),
      ]);
      setEvents(nextEvents);
      setSummary(nextSummary);
      setLastUpdated(new Date());
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to load audit events");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-base font-semibold text-iron-950">Recent Document Activity</h2>
          <p className="mt-1 text-sm text-iron-500">Filter uploads and downloads by action, outcome, actor, or project.</p>
          {lastUpdated ? <p className="mt-1 text-xs text-iron-400">Last refreshed {lastUpdated.toLocaleString()}</p> : null}
        </div>
        <div className="flex gap-2">
          <a href={documentAuditApi.csvUrl(filters())} className="rounded-md border border-iron-100 px-4 py-2 text-sm font-semibold text-iron-800">Export CSV</a>
          <button type="button" onClick={loadEvents} disabled={isLoading} className="rounded-md border border-iron-100 px-4 py-2 text-sm font-semibold text-iron-800">
            {isLoading ? "Loading..." : "Load activity"}
          </button>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <input value={action} onChange={(event) => setAction(event.target.value)} placeholder="Action" className="rounded-md border border-iron-100 px-3 py-2 text-sm" />
        <select value={outcome} onChange={(event) => setOutcome(event.target.value)} className="rounded-md border border-iron-100 px-3 py-2 text-sm">
          <option value="">All outcomes</option><option value="success">Success</option><option value="denied">Denied</option>
        </select>
        <input value={actor} onChange={(event) => setActor(event.target.value)} placeholder="Actor" className="rounded-md border border-iron-100 px-3 py-2 text-sm" />
        <input value={projectId} onChange={(event) => setProjectId(event.target.value)} placeholder="Project UUID" className="rounded-md border border-iron-100 px-3 py-2 text-sm" />
      </div>

      {error ? <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}

      {summary ? (
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <div className="rounded-md border border-iron-100 p-3"><div className="text-xs uppercase text-iron-500">Matching events</div><div className="mt-1 text-2xl font-semibold text-iron-950">{summary.total}</div></div>
          <div className="rounded-md border border-iron-100 p-3"><div className="text-xs uppercase text-iron-500">Successful</div><div className="mt-1 text-2xl font-semibold text-iron-950">{summary.by_outcome.success ?? 0}</div></div>
          <div className="rounded-md border border-iron-100 p-3"><div className="text-xs uppercase text-iron-500">Denied</div><div className="mt-1 text-2xl font-semibold text-iron-950">{summary.by_outcome.denied ?? 0}</div></div>
        </div>
      ) : null}

      {events ? (
        <div className="mt-4 overflow-hidden rounded-md border border-iron-100">
          <table className="w-full text-left text-sm">
            <thead className="bg-iron-50 text-xs uppercase tracking-wide text-iron-500">
              <tr><th className="px-3 py-2">Time</th><th className="px-3 py-2">Action</th><th className="px-3 py-2">Outcome</th><th className="px-3 py-2">Actor</th><th className="px-3 py-2">Request</th></tr>
            </thead>
            <tbody>
              {events.items.map((event, index) => (
                <tr key={`${event.request_id ?? "event"}-${event.occurred_at}-${index}`} className="border-t border-iron-100">
                  <td className="px-3 py-2 text-iron-700">{new Date(event.occurred_at).toLocaleString()}</td>
                  <td className="px-3 py-2 font-medium text-iron-950">{event.action}</td>
                  <td className="px-3 py-2 text-iron-700">{event.outcome}</td>
                  <td className="px-3 py-2 text-iron-700">{event.actor ?? "system"}</td>
                  <td className="px-3 py-2 font-mono text-xs text-iron-600">{event.request_id ?? "-"}</td>
                </tr>
              ))}
              {events.items.length === 0 ? <tr><td className="px-3 py-3 text-iron-500" colSpan={5}>No matching document activity.</td></tr> : null}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
