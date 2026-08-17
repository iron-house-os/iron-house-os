import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import { AlertTriangle, ClipboardList, FileWarning, HeartPulse, Radio, ShieldAlert, Siren } from "lucide-react";

import { Employee, FieldRecord, fieldOperationsApi } from "../api/fieldOperations";
import { useAuth } from "../contexts/AuthContext";

type View = "permits" | "actions" | "emergency" | "incidents" | "first-aid";
const TYPES = ["safety_permit", "corrective_action", "emergency_action_card", "incident", "first_aid_record"];

export function SafetyOperationsPage() {
  const { user } = useAuth();
  const [records, setRecords] = useState<FieldRecord[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [view, setView] = useState<View>("permits");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const canManageOccurrences = user?.role === "admin" || user?.role === "operations_manager";

  async function refresh() {
    try {
      const data = await fieldOperationsApi.bootstrap();
      setEmployees(data.employees);
      setRecords(data.records.filter((record) => TYPES.includes(record.record_type)));
      setError(null);
    } catch (failure) {
      setError(message(failure));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, []);

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
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
      <Metric label="Blocked permits" value={permits.filter((permit) => permit.status === "blocked").length} icon={<ShieldAlert />} />
      <Metric label="Overdue actions" value={overdue} icon={<AlertTriangle />} />
      <Metric label="Emergency cards" value={cards.length} icon={<Siren />} />
      <Metric label="Open incidents" value={incidents.filter((record) => record.status !== "closed").length} icon={<FileWarning />} />
      {canManageOccurrences ? <Metric label="First-aid records" value={firstAid.length} icon={<HeartPulse />} /> : null}
    </div>
    <nav aria-label="Safety operations sections" className="flex gap-2 overflow-x-auto rounded-xl border border-iron-100 bg-white p-2">
      {navigation.map(([key, label]) => <button key={key} type="button" onClick={() => setView(key)} className={`min-h-11 shrink-0 rounded-md px-4 py-2 text-sm font-semibold ${view === key ? "bg-brand-gold text-brand-black" : "text-iron-600"}`}>{label}</button>)}
    </nav>
    {loading ? <p className="rounded-xl border bg-white p-6 text-sm text-iron-500">Loading safety records…</p> : null}
    {!loading && view === "permits" ? <PermitView records={permits} create={create} transition={transition} /> : null}
    {!loading && view === "actions" ? <ActionView records={actions} create={create} transition={transition} /> : null}
    {!loading && view === "emergency" ? <EmergencyView records={cards} create={create} /> : null}
    {!loading && view === "incidents" ? <IncidentView records={incidents} employees={employees} canCreate={canManageOccurrences} create={create} transition={transition} /> : null}
    {!loading && view === "first-aid" && canManageOccurrences ? <FirstAidView records={firstAid} employees={employees} create={create} /> : null}
  </section>;
}

type Create = (event: FormEvent<HTMLFormElement>, recordType: string, titleField: string) => Promise<void>;
type Transition = (record: FieldRecord, status: string, prompt: string) => Promise<void>;

function PermitView({ records, create, transition }: { records: FieldRecord[]; create: Create; transition: Transition }) {
  return <Grid><form onSubmit={(event) => void create(event, "safety_permit", "project")} className="space-y-3 rounded-xl border bg-white p-6"><h2 className="font-semibold">Create permit readiness record</h2><select name="type" className="control"><option>Ground Disturbance</option><option>Confined Space</option><option>Lockout / Energy Isolation</option><option>Critical Lift</option><option>Traffic Control</option></select><Input name="project" placeholder="Project / location" /><Area name="task" placeholder="Task and work limits" /><Input name="supervisor" placeholder="Responsible supervisor" /><Area name="controls" placeholder="Controls and verification evidence required" /><label className="block text-xs font-semibold text-iron-500">Permit expiry<input name="expires" type="datetime-local" className="mt-1 w-full rounded-md border p-2 text-sm" /></label><Save>Save blocked permit</Save></form><Register empty="No permit readiness records." items={records.map((record) => <article key={record.id} className="rounded-lg border p-4"><div className="flex justify-between gap-3"><div><div className="text-xs font-semibold text-brand-gold-dark">{detail(record, "type")} · {record.work_date}</div><h3 className="font-semibold">{detail(record, "project")}</h3><p className="text-sm text-iron-600">{detail(record, "task")}</p><p className="mt-2 text-xs text-iron-500">Supervisor: {detail(record, "supervisor")} · Expires: {detail(record, "expires") || "Not set"}</p></div><Status value={record.status} /></div><p className="mt-3 rounded-md bg-iron-50 p-3 text-sm">{detail(record, "controls")}</p><div className="mt-3 flex gap-2"><Small onClick={() => void transition(record, "at_risk", "Record the review evidence and remaining risk.")}>Mark at risk</Small><Small dark onClick={() => void transition(record, "ready", "Record the field verification that supports release.")}>Verify ready</Small></div></article>)} /></Grid>;
}

function ActionView({ records, create, transition }: { records: FieldRecord[]; create: Create; transition: Transition }) {
  return <Grid><form onSubmit={(event) => void create(event, "corrective_action", "finding")} className="space-y-3 rounded-xl border bg-white p-6"><h2 className="font-semibold">Create corrective action</h2>{[["finding", "Finding"], ["risk", "Risk / consequence"], ["immediate", "Immediate control"], ["permanent", "Permanent action"], ["owner", "Action owner"]].map(([name, placeholder]) => <Input key={name} name={name} placeholder={placeholder} />)}<label className="block text-xs font-semibold text-iron-500">Due date<input required name="due" type="date" className="mt-1 w-full rounded-md border p-2 text-sm" /></label><Save>Save action</Save></form><Register empty="No corrective actions." items={records.map((record) => <article key={record.id} className="rounded-lg border p-4"><div className="flex justify-between"><div><h3 className="font-semibold">{detail(record, "finding")}</h3><p className="text-sm text-iron-500">Owner: {detail(record, "owner")} · Due: {detail(record, "due")}</p></div><Status value={record.status} /></div><p className="mt-3 text-sm"><b>Immediate:</b> {detail(record, "immediate")}</p><p className="mt-1 text-sm"><b>Permanent:</b> {detail(record, "permanent")}</p><div className="mt-3 flex gap-2"><Small onClick={() => void transition(record, "verification", "Record completion evidence for management verification.")}>Submit evidence</Small><Small dark onClick={() => void transition(record, "closed", "Record how effectiveness was verified before closure.")}>Verify and close</Small></div></article>)} /></Grid>;
}

function EmergencyView({ records, create }: { records: FieldRecord[]; create: Create }) {
  return <Grid><form onSubmit={(event) => void create(event, "emergency_action_card", "project")} className="space-y-3 rounded-xl border bg-white p-6"><h2 className="font-semibold">Create emergency action card</h2>{[["project", "Project"], ["address", "Site address / access point"], ["muster", "Muster point"], ["firstAid", "First aid location and attendant"], ["emergencyLead", "Emergency lead and contact"], ["rescue", "Rescue / evacuation method"]].map(([name, placeholder]) => <Input key={name} name={name} placeholder={placeholder} />)}<Save>Save emergency card</Save></form><Register empty="No emergency cards." items={records.map((record) => <article key={record.id} className="rounded-lg border border-red-200 bg-red-50 p-5"><div className="flex items-center gap-2"><Radio className="text-red-700" /><h3 className="font-semibold text-red-950">{detail(record, "project")}</h3></div><dl className="mt-4 grid gap-2 text-sm"><div><b>Address/access:</b> {detail(record, "address")}</div><div><b>Muster point:</b> {detail(record, "muster")}</div><div><b>First aid:</b> {detail(record, "firstAid")}</div><div><b>Emergency lead:</b> {detail(record, "emergencyLead")}</div><div><b>Rescue/evacuation:</b> {detail(record, "rescue")}</div></dl><p className="mt-3 text-xs text-red-800">Created {record.work_date}. Confirm with the crew and replace when conditions change.</p></article>)} /></Grid>;
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
function Input({ required = true, ...props }: { name: string; placeholder: string; type?: string; required?: boolean }) { return <input required={required} {...props} className="w-full rounded-md border p-2 text-sm" />; }
function Area(props: { name: string; placeholder: string }) { return <textarea required {...props} className="h-24 w-full rounded-md border p-2 text-sm" />; }
function Save({ children }: { children: ReactNode }) { return <button className="w-full rounded-md bg-brand-gold p-2 text-sm font-semibold">{children}</button>; }
function Small({ children, dark = false, onClick }: { children: ReactNode; dark?: boolean; onClick: () => void }) { return <button type="button" onClick={onClick} className={`min-h-11 rounded-md px-3 text-xs font-semibold ${dark ? "bg-iron-950 text-white" : "border"}`}>{children}</button>; }
function Metric({ label, value, icon }: { label: string; value: number; icon: ReactNode }) { return <article className="rounded-xl border bg-white p-5"><div className="flex items-center justify-between text-sm font-medium text-iron-500"><span>{label}</span>{icon}</div><div className="mt-2 text-3xl font-semibold">{value}</div></article>; }
function RestrictedNotice({ children }: { children: ReactNode }) { return <div className="h-fit rounded-xl border border-iron-100 bg-white p-5 text-sm text-iron-600">{children}</div>; }
function Status({ value }: { value: string }) { return <span className={`h-fit rounded-full px-2 py-1 text-xs font-semibold ${value === "ready" || value === "closed" || value === "recorded" ? "bg-emerald-100 text-emerald-800" : value === "at_risk" || value === "verification" || value === "under_review" ? "bg-amber-100 text-amber-800" : "bg-red-100 text-red-800"}`}>{value.replaceAll("_", " ")}</span>; }
function Register({ items, empty }: { items: ReactNode[]; empty: string }) { return <section className="rounded-xl border bg-white p-6"><div className="flex items-center gap-2"><ClipboardList className="text-brand-gold-dark" /><h2 className="font-semibold">Register</h2></div><div className="mt-4 space-y-3">{items.length ? items : <p className="rounded-md bg-iron-50 p-4 text-sm text-iron-500">{empty}</p>}</div></section>; }
