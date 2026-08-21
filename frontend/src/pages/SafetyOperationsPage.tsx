import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import { AlertTriangle, ClipboardList, Copy, Download, FileWarning, HeartPulse, QrCode, Radio, ShieldAlert, Siren } from "lucide-react";

import { Employee, FieldOperationsBootstrap, FieldRecord, SafetyAnalytics, fieldOperationsApi } from "../api/fieldOperations";
import { useAuth } from "../contexts/AuthContext";

type View = "permits" | "actions" | "emergency" | "incidents" | "first-aid";
const TYPES = ["safety_permit", "corrective_action", "emergency_action_card", "incident", "first_aid_record"];

export function SafetyOperationsPage() {
  const { user } = useAuth();
  const [records, setRecords] = useState<FieldRecord[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [projects, setProjects] = useState<FieldOperationsBootstrap["projects"]>([]);
  const [analytics, setAnalytics] = useState<SafetyAnalytics | null>(null);
  const fieldLink = useMemo(() => new URLSearchParams(window.location.search), []);
  const linkedRecordId = fieldLink.get("record");
  const linkedProjectId = fieldLink.get("projectId");
  const linkedProjectName = fieldLink.get("projectName") ?? projects.find((project) => project.id === linkedProjectId)?.name ?? "";
  const [view, setView] = useState<View>(fieldLink.get("view") === "emergency" ? "emergency" : "permits");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const canManageOccurrences = user?.role === "admin" || user?.role === "operations_manager";

  async function refresh() {
    try {
      const data = await fieldOperationsApi.bootstrap();
      const safetyAnalytics = canManageOccurrences ? await fieldOperationsApi.safetyAnalytics() : null;
      setEmployees(data.employees);
      setProjects(data.projects);
      setRecords(data.records.filter((record) => TYPES.includes(record.record_type)));
      setAnalytics(safetyAnalytics);
      setError(null);
    } catch (failure) {
      setError(message(failure));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, []);
  useEffect(() => {
    if (!loading && view === "emergency" && linkedRecordId) {
      document.getElementById(`emergency-card-${linkedRecordId}`)?.scrollIntoView({ block: "start" });
    }
  }, [linkedRecordId, loading, view]);

  const permits = records.filter((record) => record.record_type === "safety_permit");
  const actions = records.filter((record) => record.record_type === "corrective_action");
  const cards = records.filter((record) => record.record_type === "emergency_action_card");
  const incidents = records.filter((record) => record.record_type === "incident");
  const firstAid = records.filter((record) => record.record_type === "first_aid_record");
  const overdue = useMemo(
    () => actions.filter((record) => record.status !== "closed" && detail(record, "due") && new Date(detail(record, "due")).getTime() < Date.now()).length,
    [actions],
  );

  async function create(event: FormEvent<HTMLFormElement>, recordType: string, titleField: string) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const employeeId = String(data.get("employee_id") ?? "");
    const details = Object.fromEntries(
      [...data.entries()]
        .filter(([key]) => key !== "employee_id")
        .map(([key, value]) => [key, String(value)]),
    );
    const occurredAt = String(data.get("occurred_at") ?? "");
    try {
      await fieldOperationsApi.createRecord({
        record_type: recordType,
        project_id: linkedProjectId || null,
        employee_id: employeeId || null,
        work_date: occurredAt.slice(0, 10) || new Date().toISOString().slice(0, 10),
        title: String(data.get(titleField)),
        severity: recordType === "first_aid_record" ? "none" : recordType === "emergency_action_card" ? "medium" : "high",
        details,
      });
      form.reset();
      await refresh();
    } catch (failure) {
      setError(message(failure));
    }
  }

  async function transition(record: FieldRecord, status: string, prompt: string) {
    const evidence = window.prompt(prompt, String(record.details.verification_evidence ?? ""));
    if (!evidence?.trim()) return;
    try {
      await fieldOperationsApi.updateSafetyStatus(record.id, status, evidence);
      await refresh();
    } catch (failure) {
      setError(message(failure));
    }
  }

  const navigation: Array<[View, string]> = [
    ["permits", "High-risk permits"],
    ["actions", "Corrective actions"],
    ["emergency", "Emergency cards"],
    ["incidents", "Incidents / near misses"],
    ...(canManageOccurrences ? [["first-aid", "First-aid occurrences"] as [View, string]] : []),
  ];

  return <section className="space-y-6">
    <header className="ihos-brand-surface rounded-xl border border-brand-gold/30 p-6 text-white shadow-brand">
      <div className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-gold">Build 221</div>
      <h1 className="mt-2 text-3xl font-semibold text-brand-silver">Safety Operations Control</h1>
      <p className="mt-2 max-w-3xl text-sm text-iron-100">Database-backed permit readiness, corrective actions, emergency cards, incident review and privacy-scoped first-aid occurrence records.</p>
    </header>
    {error ? <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div> : null}
    {linkedProjectId ? <div className="rounded-md border border-brand-gold/40 bg-brand-gold/10 p-3 text-sm font-semibold text-iron-800">New safety records will be linked to {linkedProjectName || linkedProjectId}.</div> : null}
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
      <Metric label="Blocked permits" value={analytics?.blocked_permits ?? permits.filter((permit) => permit.status === "blocked").length} icon={<ShieldAlert />} />
      <Metric label="Overdue actions" value={analytics?.overdue_corrective_actions ?? overdue} icon={<AlertTriangle />} />
      <Metric label="Emergency cards" value={analytics?.active_emergency_cards ?? cards.length} icon={<Siren />} />
      <Metric label="Open incidents" value={analytics?.open_incidents ?? incidents.filter((record) => record.status !== "closed").length} icon={<FileWarning />} />
      {canManageOccurrences ? <Metric label="First-aid records" value={firstAid.length} icon={<HeartPulse />} /> : null}
    </div>
    {canManageOccurrences && analytics ? <section className="rounded-xl border border-iron-100 bg-white p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><h2 className="font-semibold text-iron-950">Management safety analytics</h2><p className="mt-1 max-w-3xl text-sm text-iron-500">Operational indicators as of {analytics.as_of}. These are workflow signals, not legal or regulatory compliance conclusions.</p></div>
        <a href={fieldOperationsApi.safetyAuditExportUrl} className="inline-flex min-h-11 items-center gap-2 rounded-md border border-brand-gold px-3 text-sm font-semibold text-brand-gold-dark"><Download className="h-4 w-4" />Export audit CSV</a>
      </div>
      <dl className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <AnalyticsFact label="FLHAs · 30 days" value={analytics.flha_last_30_days} />
        <AnalyticsFact label="Toolbox talks · 30 days" value={analytics.toolbox_talks_last_30_days} />
        <AnalyticsFact label="Credentials expiring · 60 days" value={analytics.credentials_expiring_60_days} />
        <AnalyticsFact label="Expired credentials" value={analytics.credentials_expired} />
        <AnalyticsFact label="Exportable control records" value={analytics.audit_export_records} />
      </dl>
      <p className="mt-4 rounded-md bg-iron-50 p-3 text-xs leading-5 text-iron-600">The audit export contains control metadata only. Incident and first-aid occurrence records, narrative details, worker identifiers and submitter identities are excluded.</p>
    </section> : null}
    <nav aria-label="Safety operations sections" className="flex gap-2 overflow-x-auto rounded-xl border border-iron-100 bg-white p-2">
      {navigation.map(([key, label]) => <button key={key} type="button" onClick={() => setView(key)} className={`min-h-11 shrink-0 rounded-md px-4 py-2 text-sm font-semibold ${view === key ? "bg-brand-gold text-brand-black" : "text-iron-600"}`}>{label}</button>)}
    </nav>
    {loading ? <p className="rounded-xl border bg-white p-6 text-sm text-iron-500">Loading safety records…</p> : null}
    {!loading && view === "permits" ? <PermitView records={permits} create={create} transition={transition} projectName={linkedProjectName} /> : null}
    {!loading && view === "actions" ? <ActionView records={actions} create={create} transition={transition} /> : null}
    {!loading && view === "emergency" ? <EmergencyView records={cards} create={create} projectName={linkedProjectName} /> : null}
    {!loading && view === "incidents" ? <IncidentView records={incidents} employees={employees} canCreate={canManageOccurrences} create={create} transition={transition} /> : null}
    {!loading && view === "first-aid" && canManageOccurrences ? <FirstAidView records={firstAid} employees={employees} create={create} /> : null}
  </section>;
}

type Create = (event: FormEvent<HTMLFormElement>, recordType: string, titleField: string) => Promise<void>;
type Transition = (record: FieldRecord, status: string, prompt: string) => Promise<void>;

function PermitView({ records, create, transition, projectName }: { records: FieldRecord[]; create: Create; transition: Transition; projectName: string }) {
  return <Grid><form onSubmit={(event) => void create(event, "safety_permit", "project")} className="space-y-3 rounded-xl border bg-white p-6"><h2 className="font-semibold">Create permit readiness record</h2><select name="type" className="control"><option>Ground Disturbance</option><option>Confined Space</option><option>Lockout / Energy Isolation</option><option>Critical Lift</option><option>Traffic Control</option></select><Input name="project" placeholder="Project / location" defaultValue={projectName} /><Area name="task" placeholder="Task and work limits" /><Input name="supervisor" placeholder="Responsible supervisor" /><Area name="controls" placeholder="Controls and verification evidence required" /><label className="block text-xs font-semibold text-iron-500">Permit expiry<input name="expires" type="datetime-local" className="mt-1 w-full rounded-md border p-2 text-sm" /></label><Save>Save blocked permit</Save></form><Register empty="No permit readiness records." items={records.map((record) => <article key={record.id} className="rounded-lg border p-4"><div className="flex justify-between gap-3"><div><div className="text-xs font-semibold text-brand-gold-dark">{detail(record, "type")} · {record.work_date}</div><h3 className="font-semibold">{detail(record, "project")}</h3><p className="text-sm text-iron-600">{detail(record, "task")}</p><p className="mt-2 text-xs text-iron-500">Supervisor: {detail(record, "supervisor")} · Expires: {detail(record, "expires") || "Not set"}</p></div><Status value={record.status} /></div><p className="mt-3 rounded-md bg-iron-50 p-3 text-sm">{detail(record, "controls")}</p><div className="mt-3 flex gap-2"><Small onClick={() => void transition(record, "at_risk", "Record the review evidence and remaining risk.")}>Mark at risk</Small><Small dark onClick={() => void transition(record, "ready", "Record the field verification that supports release.")}>Verify ready</Small></div></article>)} /></Grid>;
}

function ActionView({ records, create, transition }: { records: FieldRecord[]; create: Create; transition: Transition }) {
  return <Grid><form onSubmit={(event) => void create(event, "corrective_action", "finding")} className="space-y-3 rounded-xl border bg-white p-6"><h2 className="font-semibold">Create corrective action</h2>{[["finding", "Finding"], ["risk", "Risk / consequence"], ["immediate", "Immediate control"], ["permanent", "Permanent action"], ["owner", "Action owner"]].map(([name, placeholder]) => <Input key={name} name={name} placeholder={placeholder} />)}<label className="block text-xs font-semibold text-iron-500">Due date<input required name="due" type="date" className="mt-1 w-full rounded-md border p-2 text-sm" /></label><Save>Save action</Save></form><Register empty="No corrective actions." items={records.map((record) => <article key={record.id} className="rounded-lg border p-4"><div className="flex justify-between"><div><h3 className="font-semibold">{detail(record, "finding")}</h3><p className="text-sm text-iron-500">Owner: {detail(record, "owner")} · Due: {detail(record, "due")}</p></div><Status value={record.status} /></div><p className="mt-3 text-sm"><b>Immediate:</b> {detail(record, "immediate")}</p><p className="mt-1 text-sm"><b>Permanent:</b> {detail(record, "permanent")}</p><div className="mt-3 flex gap-2"><Small onClick={() => void transition(record, "verification", "Record completion evidence for management verification.")}>Submit evidence</Small><Small dark onClick={() => void transition(record, "closed", "Record how effectiveness was verified before closure.")}>Verify and close</Small></div></article>)} /></Grid>;
}

function EmergencyView({ records, create, projectName }: { records: FieldRecord[]; create: Create; projectName: string }) {
  return <Grid><form onSubmit={(event) => void create(event, "emergency_action_card", "project")} className="space-y-3 rounded-xl border bg-white p-6"><h2 className="font-semibold">Create emergency action card</h2>{[["project", "Project"], ["address", "Site address / access point"], ["muster", "Muster point"], ["firstAid", "First aid location and attendant"], ["emergencyLead", "Emergency lead and contact"], ["rescue", "Rescue / evacuation method"]].map(([name, placeholder]) => <Input key={name} name={name} placeholder={placeholder} defaultValue={name === "project" ? projectName : undefined} />)}<Save>Save emergency card</Save></form><Register empty="No emergency cards." items={records.map((record) => <article id={`emergency-card-${record.id}`} key={record.id} className="scroll-mt-6 rounded-lg border border-red-200 bg-red-50 p-5"><div className="flex items-center gap-2"><Radio className="text-red-700" /><h3 className="font-semibold text-red-950">{detail(record, "project")}</h3></div><dl className="mt-4 grid gap-2 text-sm"><div><dt className="font-semibold">Address/access:</dt><dd>{detail(record, "address")}</dd></div><div><dt className="font-semibold">Muster point:</dt><dd>{detail(record, "muster")}</dd></div><div><dt className="font-semibold">First aid:</dt><dd>{detail(record, "firstAid")}</dd></div><div><dt className="font-semibold">Emergency lead:</dt><dd>{detail(record, "emergencyLead")}</dd></div><div><dt className="font-semibold">Rescue/evacuation:</dt><dd>{detail(record, "rescue")}</dd></div></dl><p className="mt-3 text-xs text-red-800">Created {record.work_date}. Confirm with the crew and replace when conditions change.</p><EmergencyFieldAccess record={record} /></article>)} /></Grid>;
}

function EmergencyFieldAccess({ record }: { record: FieldRecord }) {
  const [qrSvg, setQrSvg] = useState("");
  const [qrError, setQrError] = useState("");
  const [copyStatus, setCopyStatus] = useState("");
  const fieldUrl = `${window.location.origin}/safety-operations?view=emergency&record=${record.id}`;

  useEffect(() => {
    let active = true;
    void import("qrcode")
      .then(({ default: QRCode }) => QRCode.toString(fieldUrl, { type: "svg", errorCorrectionLevel: "M", margin: 1, width: 192, color: { dark: "#0b0d11", light: "#ffffff" } }))
      .then((value) => { if (active) setQrSvg(value); })
      .catch(() => { if (active) setQrError("QR code unavailable. Use Copy field link instead."); });
    return () => { active = false; };
  }, [fieldUrl]);

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(fieldUrl);
      setCopyStatus("Field link copied.");
    } catch {
      setCopyStatus("Copy unavailable. Open the field link and copy it from Safari.");
    }
  }

  const qrDataUrl = qrSvg ? `data:image/svg+xml,${encodeURIComponent(qrSvg)}` : "";
  return <div className="mt-4 rounded-lg border border-red-200 bg-white p-4 text-iron-900">
    <div className="flex flex-wrap gap-2">
      <a href={fieldOperationsApi.emergencyActionCardPdfUrl(record.id)} className="inline-flex min-h-11 items-center gap-2 rounded-md bg-iron-950 px-3 text-sm font-semibold text-white"><Download className="h-4 w-4" />PDF / save offline</a>
      <button type="button" onClick={() => void copyLink()} className="inline-flex min-h-11 items-center gap-2 rounded-md border border-iron-200 px-3 text-sm font-semibold"><Copy className="h-4 w-4" />Copy field link</button>
    </div>
    {copyStatus ? <p role="status" className="mt-2 text-xs text-iron-600">{copyStatus}</p> : null}
    <details className="mt-3">
      <summary className="flex min-h-11 cursor-pointer items-center gap-2 text-sm font-semibold"><QrCode className="h-4 w-4" />Show QR field link</summary>
      <div className="mt-2 flex flex-wrap items-center gap-4">{qrDataUrl ? <><img src={qrDataUrl} alt={`QR field link for ${detail(record, "project") || record.title}`} className="h-48 w-48 border bg-white p-2" /><a href={qrDataUrl} download={`emergency-action-card-${record.id}.svg`} className="min-h-11 rounded-md border border-brand-gold px-3 py-3 text-sm font-semibold text-brand-gold-dark">Download QR SVG</a></> : <p role={qrError ? "alert" : undefined} className="text-sm text-iron-500">{qrError || "Preparing QR code…"}</p>}</div>
      <p className="mt-2 text-xs leading-5 text-iron-600">The QR contains only this authenticated IHOS link—no password or access token. Sign-in is still required.</p>
    </details>
  </div>;
}

function IncidentView({ records, employees, canCreate, create, transition }: { records: FieldRecord[]; employees: Employee[]; canCreate: boolean; create: Create; transition: Transition }) {
  return <Grid>
    {canCreate ? <form onSubmit={(event) => void create(event, "incident", "title")} className="space-y-3 rounded-xl border bg-white p-6">
      <h2 className="font-semibold">Report incident or near miss</h2>
      <select required name="occurrence_kind" className="w-full rounded-md border p-2 text-sm"><option value="near_miss">Near miss</option><option value="incident">Incident</option></select>
      <Input name="title" placeholder="Short operational title" />
      <EmployeeSelect employees={employees} optional />
      <label className="block text-xs font-semibold text-iron-500">Occurred at<input required name="occurred_at" type="datetime-local" className="mt-1 w-full rounded-md border p-2 text-sm" /></label>
      <Input name="location" placeholder="Project / location" />
      <Area name="description" placeholder="What happened" />
      <Area name="immediate_controls" placeholder="Immediate controls taken" />
      <Input name="witnesses" placeholder="Witnesses, if any" required={false} />
      <Save>Save reported occurrence</Save>
    </form> : <RestrictedNotice>Incident and near-miss creation is limited to operations management here. Forepersons can submit from their portal.</RestrictedNotice>}
    <Register empty="No incident or near-miss records." items={records.map((record) => <article key={record.id} className="rounded-lg border p-4"><div className="flex justify-between gap-3"><div><div className="text-xs font-semibold uppercase text-brand-gold-dark">{detail(record, "occurrence_kind").replace("_", " ")} · {record.work_date}</div><h3 className="font-semibold">{record.title}</h3><p className="text-sm text-iron-500">{detail(record, "location")}{employeeName(record.employee_id, employees) ? ` · ${employeeName(record.employee_id, employees)}` : ""}</p></div><Status value={record.status} /></div><p className="mt-3 text-sm">{detail(record, "description")}</p><p className="mt-2 rounded-md bg-iron-50 p-3 text-sm"><b>Immediate controls:</b> {detail(record, "immediate_controls")}</p><div className="mt-3 flex gap-2">{record.status === "reported" ? <Small onClick={() => void transition(record, "under_review", "Record the initial review assignment or evidence.")}>Start review</Small> : null}{record.status === "under_review" ? <Small dark onClick={() => void transition(record, "closed", "Record the evidence and management verification supporting closure.")}>Verify and close</Small> : null}</div></article>)} />
  </Grid>;
}

function FirstAidView({ records, employees, create }: { records: FieldRecord[]; employees: Employee[]; create: Create }) {
  return <Grid>
    <form onSubmit={(event) => void create(event, "first_aid_record", "title")} className="space-y-3 rounded-xl border bg-white p-6">
      <h2 className="font-semibold">Record first-aid occurrence</h2>
      <p className="rounded-md bg-amber-50 p-3 text-xs leading-5 text-amber-900">Minimum necessary operational record. Do not enter a diagnosis, medical conclusion, or unrelated health history.</p>
      <Input name="title" placeholder="Record title" />
      <EmployeeSelect employees={employees} />
      <label className="block text-xs font-semibold text-iron-500">Occurred at<input required name="occurred_at" type="datetime-local" className="mt-1 w-full rounded-md border p-2 text-sm" /></label>
      <Input name="location" placeholder="Project / location" />
      <Input name="first_aid_attendant" placeholder="First-aid attendant" />
      <Area name="general_nature" placeholder="General nature of occurrence — no diagnosis" />
      <Area name="aid_provided" placeholder="Aid provided" />
      <select required name="outcome" defaultValue="" className="w-full rounded-md border p-2 text-sm"><option value="" disabled>Recorded outcome</option><option value="returned_to_work">Returned to work</option><option value="referred_for_further_assessment">Referred for further assessment</option><option value="transported_for_further_assessment">Transported for further assessment</option></select>
      <Input name="follow_up" placeholder="Operational follow-up, if any" required={false} />
      <Save>Save confidential record</Save>
    </form>
    <Register empty="No first-aid occurrence records." items={records.map((record) => <article key={record.id} className="rounded-lg border border-amber-200 bg-amber-50/40 p-4"><div className="flex justify-between gap-3"><div><div className="text-xs font-semibold text-brand-gold-dark">{record.work_date} · {employeeName(record.employee_id, employees) || "Worker record"}</div><h3 className="font-semibold">{record.title}</h3><p className="text-sm text-iron-500">{detail(record, "location")} · Attendant: {detail(record, "first_aid_attendant")}</p></div><Status value={record.status} /></div><p className="mt-3 text-sm"><b>General nature:</b> {detail(record, "general_nature")}</p><p className="mt-2 text-sm"><b>Aid provided:</b> {detail(record, "aid_provided")}</p><p className="mt-2 text-xs text-iron-500">Outcome: {detail(record, "outcome").replaceAll("_", " ")}</p></article>)} />
  </Grid>;
}

function EmployeeSelect({ employees, optional = false }: { employees: Employee[]; optional?: boolean }) {
  return <select required={!optional} name="employee_id" defaultValue="" className="w-full rounded-md border p-2 text-sm"><option value="">{optional ? "Affected worker, if applicable" : "Select worker"}</option>{employees.map((employee) => <option key={employee.id} value={employee.id}>{employee.first_name} {employee.last_name}</option>)}</select>;
}

function detail(record: FieldRecord, key: string) { const value = record.details[key]; return typeof value === "string" ? value : ""; }
function employeeName(id: string | null, employees: Employee[]) { const employee = employees.find((item) => item.id === id); return employee ? `${employee.first_name} ${employee.last_name}` : ""; }
function message(value: unknown) { return value instanceof Error ? value.message : "Unable to complete the safety operation."; }
function Grid({ children }: { children: ReactNode }) { return <div className="grid gap-6 xl:grid-cols-[390px_1fr]">{children}</div>; }
function Input({ required = true, ...props }: { name: string; placeholder: string; type?: string; required?: boolean; defaultValue?: string }) { return <input required={required} {...props} className="w-full rounded-md border p-2 text-sm" />; }
function Area(props: { name: string; placeholder: string }) { return <textarea required {...props} className="h-24 w-full rounded-md border p-2 text-sm" />; }
function Save({ children }: { children: ReactNode }) { return <button className="w-full rounded-md bg-brand-gold p-2 text-sm font-semibold">{children}</button>; }
function Small({ children, dark = false, onClick }: { children: ReactNode; dark?: boolean; onClick: () => void }) { return <button type="button" onClick={onClick} className={`min-h-11 rounded-md px-3 text-xs font-semibold ${dark ? "bg-iron-950 text-white" : "border"}`}>{children}</button>; }
function Metric({ label, value, icon }: { label: string; value: number; icon: ReactNode }) { return <article className="rounded-xl border bg-white p-5"><div className="flex items-center justify-between text-sm font-medium text-iron-500"><span>{label}</span>{icon}</div><div className="mt-2 text-3xl font-semibold">{value}</div></article>; }
function AnalyticsFact({ label, value }: { label: string; value: number }) { return <div className="rounded-lg bg-iron-50 p-4"><dt className="text-xs font-semibold uppercase tracking-wide text-iron-500">{label}</dt><dd className="mt-1 text-2xl font-semibold text-iron-950">{value}</dd></div>; }
function RestrictedNotice({ children }: { children: ReactNode }) { return <div className="h-fit rounded-xl border border-iron-100 bg-white p-5 text-sm text-iron-600">{children}</div>; }
function Status({ value }: { value: string }) { return <span className={`h-fit rounded-full px-2 py-1 text-xs font-semibold ${value === "ready" || value === "closed" || value === "recorded" ? "bg-emerald-100 text-emerald-800" : value === "at_risk" || value === "verification" || value === "under_review" ? "bg-amber-100 text-amber-800" : "bg-red-100 text-red-800"}`}>{value.replaceAll("_", " ")}</span>; }
function Register({ items, empty }: { items: ReactNode[]; empty: string }) { return <section className="rounded-xl border bg-white p-6"><div className="flex items-center gap-2"><ClipboardList className="text-brand-gold-dark" /><h2 className="font-semibold">Register</h2></div><div className="mt-4 space-y-3">{items.length ? items : <p className="rounded-md bg-iron-50 p-4 text-sm text-iron-500">{empty}</p>}</div></section>; }
