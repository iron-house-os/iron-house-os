from __future__ import annotations

import json
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .config import AgentSettings
from .health import repositories_health
from .store import AGENT_ROLES, JobStore

StateProvider = Callable[[], dict[str, Any]]


_DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Iron House Agent Control</title>
  <style>
    :root { color-scheme: dark; --bg:#0b0d10; --panel:#15191e; --line:#30363d;
      --text:#f0f3f6; --muted:#9ca7b2; --gold:#d6ad4a; --green:#50c878;
      --red:#ff6b6b; --blue:#67a7ff; }
    * { box-sizing:border-box; }
    body { margin:0; background:linear-gradient(135deg,#090b0e,#14181d); color:var(--text);
      font:14px/1.45 Inter,ui-sans-serif,system-ui,sans-serif; min-height:100vh; }
    main { width:min(1440px,94vw); margin:0 auto; padding:32px 0 48px; }
    header { display:flex; align-items:flex-end; justify-content:space-between; gap:24px;
      border-bottom:1px solid var(--line); padding-bottom:20px; }
    h1 { margin:0; letter-spacing:.04em; font-size:clamp(24px,3vw,38px); }
    .eyebrow { color:var(--gold); text-transform:uppercase; letter-spacing:.18em;
      font-weight:700; font-size:12px; }
    .muted { color:var(--muted); }
    .cards { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px;
      margin:22px 0; }
    .card,.panel { background:rgba(21,25,30,.94); border:1px solid var(--line);
      border-radius:12px; box-shadow:0 12px 30px rgba(0,0,0,.22); }
    .card { padding:18px; }
    .metric { font-size:32px; font-weight:750; margin-top:4px; }
    .layout { display:grid; grid-template-columns:1.25fr .75fr; gap:16px; }
    .panel { overflow:hidden; margin-bottom:16px; }
    .panel h2 { font-size:15px; letter-spacing:.08em; text-transform:uppercase;
      margin:0; padding:16px 18px; border-bottom:1px solid var(--line); }
    .panel-body { padding:16px 18px; }
    table { width:100%; border-collapse:collapse; }
    th,td { padding:11px 10px; border-bottom:1px solid #252b31; text-align:left;
      vertical-align:top; }
    th { color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.08em; }
    tr:last-child td { border-bottom:0; }
    .pill { display:inline-flex; border:1px solid var(--line); border-radius:999px;
      padding:3px 8px; font-size:11px; font-weight:700; text-transform:uppercase; }
    .succeeded,.healthy,.running,.accepted,.ready { color:var(--green); }
    .failed,.error,.blocked,.missing { color:var(--red); }
    .queued,.dirty { color:var(--gold); }
    .role-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; }
    .role { padding:10px 11px; border:1px solid #282f36; border-radius:8px; }
    .repo { padding:12px 0; border-bottom:1px solid #252b31; }
    .repo:last-child { border:0; }
    .repo-head { display:flex; justify-content:space-between; gap:14px; }
    .empty { color:var(--muted); padding:18px 0; text-align:center; }
    code { color:#d9e2eb; font-size:12px; }
    @media (max-width:900px) { .cards{grid-template-columns:repeat(2,1fr)}
      .layout{grid-template-columns:1fr} }
    @media (max-width:520px) { .cards{grid-template-columns:1fr} header{align-items:flex-start;
      flex-direction:column} main{width:92vw;padding-top:20px} }
  </style>
</head>
<body>
<main>
  <header>
    <div><div class="eyebrow">Iron House Development Platform</div>
      <h1>Agent Control</h1><div class="muted">Feature branches only · Production locked</div></div>
    <div class="muted" id="updated">Loading…</div>
  </header>
  <section class="cards">
    <div class="card"><div class="muted">Active agents</div><div class="metric" id="active">0</div></div>
    <div class="card"><div class="muted">Queued jobs</div><div class="metric" id="queued">0</div></div>
    <div class="card"><div class="muted">Completed jobs</div><div class="metric" id="completed">0</div></div>
    <div class="card"><div class="muted">Healthy repositories</div><div class="metric" id="healthy">0</div></div>
  </section>
  <section class="layout">
    <div>
      <div class="panel"><h2>Current jobs</h2><div class="panel-body" id="current"></div></div>
      <div class="panel"><h2>Queue</h2><div class="panel-body" id="queue"></div></div>
      <div class="panel"><h2>Build history</h2><div class="panel-body" id="history"></div></div>
    </div>
    <aside>
      <div class="panel"><h2>Agent roles</h2><div class="panel-body role-grid" id="roles"></div></div>
      <div class="panel"><h2>Repository health</h2><div class="panel-body" id="repos"></div></div>
      <div class="panel"><h2>GitHub intake</h2><div class="panel-body" id="intake"></div></div>
    </aside>
  </section>
</main>
<script>
const esc = value => String(value ?? '').replace(/[&<>'"]/g, char =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
const shortId = value => value ? String(value).slice(0,8) : '—';
function jobsTable(rows) {
  if (!rows.length) return '<div class="empty">No jobs</div>';
  return `<table><thead><tr><th>Job</th><th>Project</th><th>Agent</th><th>Status</th><th>Branch</th></tr></thead>
    <tbody>${rows.map(job => `<tr><td><strong>${esc(job.title)}</strong><br><code>${shortId(job.id)} · #${esc(job.issue_number)}</code></td>
    <td>${esc(job.project_key)}</td><td>${esc(job.role)}</td><td><span class="pill ${esc(job.status)}">${esc(job.status)}</span></td>
    <td><code>${esc(job.branch || 'pending')}</code></td></tr>`).join('')}</tbody></table>`;
}
function intakePanel(state) {
  const sources = state.intake_sources || [];
  const history = state.intake_history || [];
  const sourceRows = sources.map(source => `<div class="repo"><div class="repo-head">
    <strong>${esc(source.project_key)}</strong><span class="pill ${esc(source.state)}">${esc(source.state)}</span></div>
    <div class="muted">${esc(source.detail)}</div></div>`).join('');
  const historyRows = history.slice(0, 8).map(item => `<div class="repo"><div class="repo-head">
    <strong>${esc(item.project_key)} #${esc(item.issue_number)}</strong>
    <span class="pill ${esc(item.status)}">${esc(item.status)}</span></div>
    <div class="muted">${esc(item.role || 'no role')} · ${esc(item.detail)}</div></div>`).join('');
  return sourceRows + historyRows || '<div class="empty">Waiting for first intake check</div>';
}
function render(state) {
  document.getElementById('active').textContent = state.current_jobs.length;
  document.getElementById('queued').textContent = state.queue.length;
  document.getElementById('completed').textContent = state.history.length;
  document.getElementById('healthy').textContent = state.repositories.filter(r => r.status === 'healthy').length;
  document.getElementById('current').innerHTML = jobsTable(state.current_jobs);
  document.getElementById('queue').innerHTML = jobsTable(state.queue);
  document.getElementById('history').innerHTML = jobsTable(state.history);
  document.getElementById('roles').innerHTML = state.agent_roles.map(role =>
    `<div class="role"><strong>${esc(role.name)}</strong><br><span class="muted">${esc(role.state)}</span></div>`).join('');
  document.getElementById('repos').innerHTML = state.repositories.map(repo =>
    `<div class="repo"><div class="repo-head"><strong>${esc(repo.name)}</strong>
    <span class="pill ${esc(repo.status)}">${esc(repo.status)}</span></div>
    <div class="muted">${esc(repo.detail)}</div><code>${esc(repo.branch || '—')} · ${esc(repo.commit || '—')}</code></div>`).join('');
  document.getElementById('intake').innerHTML = intakePanel(state);
  document.getElementById('updated').textContent = `Updated ${new Date(state.generated_at).toLocaleString()}`;
}
async function refresh() {
  try { const response = await fetch('/api/state', {cache:'no-store'});
    if (!response.ok) throw new Error(`HTTP ${response.status}`); render(await response.json()); }
  catch (error) { document.getElementById('updated').textContent = `Dashboard unavailable: ${error.message}`; }
}
refresh(); setInterval(refresh, 5000);
</script>
</body>
</html>
"""


def build_state(settings: AgentSettings, store: JobStore) -> dict[str, Any]:
    snapshot = store.snapshot()
    role_state = []
    for role in AGENT_ROLES:
        active = sum(1 for job in snapshot["current_jobs"] if job["role"] == role)
        queued = sum(1 for job in snapshot["queue"] if job["role"] == role)
        state = f"{active} active" if active else (f"{queued} queued" if queued else "ready")
        role_state.append({"name": role, "state": state})
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "production_locked": True,
        "agent_roles": role_state,
        "repositories": repositories_health(settings),
        **snapshot,
    }


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "IronHouseAgentDashboard/1.0"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send(HTTPStatus.OK, "text/html; charset=utf-8", _DASHBOARD_HTML.encode())
            return
        if path == "/healthz":
            self._json(HTTPStatus.OK, {"status": "ok", "production_locked": True})
            return
        if path == "/api/state":
            state_provider = self.server.state_provider
            self._json(HTTPStatus.OK, state_provider())
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        self._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "dashboard is read-only"})

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        self._send(status, "application/json; charset=utf-8", json.dumps(payload).encode())

    def _send(self, status: HTTPStatus, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(body)


def create_dashboard_server(
    settings: AgentSettings, store: JobStore, state_provider: StateProvider | None = None
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(
        (settings.dashboard_host, settings.dashboard_port), DashboardHandler
    )
    server.state_provider = state_provider or (lambda: build_state(settings, store))
    return server


def start_dashboard_thread(
    settings: AgentSettings, store: JobStore, state_provider: StateProvider | None = None
) -> tuple[ThreadingHTTPServer, threading.Thread]:
    server = create_dashboard_server(settings, store, state_provider)
    thread = threading.Thread(target=server.serve_forever, name="agent-dashboard", daemon=True)
    thread.start()
    return server, thread
