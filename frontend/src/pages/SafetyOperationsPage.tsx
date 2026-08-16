import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import { AlertTriangle, ClipboardList, Radio, ShieldAlert, Siren } from "lucide-react";
import { FieldRecord, fieldOperationsApi } from "../api/fieldOperations";

type View = "permits" | "actions" | "emergency";
const TYPES = ["safety_permit", "corrective_action", "emergency_action_card"];

export function SafetyOperationsPage() {
  const [records, setRecords] = useState<FieldRecord[]>([]);
  const [view, setView] = useState<View>("permits");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  async function refresh() { try { const data = await fieldOperationsApi.bootstrap(); setRecords(data.records.filter((r) => TYPES.includes(r.record_type))); setError(null); } catch (failure) { setError(message(failure)); } finally { setLoading(false); } }
  useEffect(() => { void refresh(); }, []);
  const permits = records.filter((r) => r.record_type === "safety_permit");
  const actions = records.filter((r) => r.record_type === "corrective_action");
  const cards = records.filter((r) => r.record_type === "emergency_action_card");
  const overdue = useMemo(() => actions.filter((r) => r.status !== "closed" && detail(r,"due") && new Date(detail(r,"due")).getTime() < Date.now()).length, [actions]);

  async function create(event: FormEvent<HTMLFormElement>, recordType: string, titleField: string) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
    const details = Object.fromEntries([...data.entries()].map(([key,value]) => [key,String(value)]));
    try { await fieldOperationsApi.createRecord({ record_type: recordType, work_date: new Date().toISOString().slice(0,10), title: String(data.get(titleField)), severity: recordType === "emergency_action_card" ? "medium" : "high", details }); form.reset(); await refresh(); }
    catch (failure) { setError(message(failure)); }
  }
  async function transition(record: FieldRecord, status: string, prompt: string) {
    const evidence = window.prompt(prompt, String(record.details.verification_evidence ?? "")); if (!evidence?.trim()) return;
    try { await fieldOperationsApi.updateSafetyStatus(record.id, status, evidence); await refresh(); } catch (failure) { setError(message(failure)); }
  }

  return <section className="space-y-6">
    <header className="ihos-brand-surface rounded-xl border border-brand-gold/30 p-6 text-white shadow-brand"><div className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-gold">Build 221</div><h1 className="mt-2 text-3xl font-semibold text-brand-silver">Safety Operations Control</h1><p className="mt-2 max-w-3xl text-sm text-iron-100">Database-backed permit readiness, corrective-action verification and project emergency action cards.</p></header>
    {error ? <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div> : null}
    <div className="grid gap-4 md:grid-cols-3"><Metric label="Blocked permits" value={permits.filter((p) => p.status === "blocked").length} icon={<ShieldAlert />} /><Metric label="Overdue actions" value={overdue} icon={<AlertTriangle />} /><Metric label="Emergency cards" value={cards.length} icon={<Siren />} /></div>
    <nav aria-label="Safety operations sections" className="flex gap-2 overflow-x-auto rounded-xl border border-iron-100 bg-white p-2">{[["permits","High-risk permits"],["actions","Corrective actions"],["emergency","Emergency cards"]].map(([key,label]) => <button key={key} onClick={() => setView(key as View)} className={`min-h-11 rounded-md px-4 py-2 text-sm font-semibold ${view === key ? "bg-brand-gold text-brand-black" : "text-iron-600"}`}>{label}</button>)}</nav>
    {loading ? <p className="rounded-xl border bg-white p-6 text-sm text-iron-500">Loading safety records…</p> : null}
    {!loading && view === "permits" ? <PermitView records={permits} create={create} transition={transition} /> : null}
    {!loading && view === "actions" ? <ActionView records={actions} create={create} transition={transition} /> : null}
    {!loading && view === "emergency" ? <EmergencyView records={cards} create={create} /> : null}
  </section>;
}

type Create = (event: FormEvent<HTMLFormElement>, recordType: string, titleField: string) => Promise<void>;
type Transition = (record: FieldRecord, status: string, prompt: string) => Promise<void>;

function PermitView({records,create,transition}:{records:FieldRecord[];create:Create;transition:Transition}) { return <Grid><form onSubmit={(e) => void create(e,"safety_permit","project")} className="space-y-3 rounded-xl border bg-white p-6"><h2 className="font-semibold">Create permit readiness record</h2><select name="type" className="control"><option>Ground Disturbance</option><option>Confined Space</option><option>Lockout / Energy Isolation</option><option>Critical Lift</option><option>Traffic Control</option></select><Input name="project" placeholder="Project / location" /><Area name="task" placeholder="Task and work limits" /><Input name="supervisor" placeholder="Responsible supervisor" /><Area name="controls" placeholder="Controls and verification evidence required" /><label className="block text-xs font-semibold text-iron-500">Permit expiry<input name="expires" type="datetime-local" className="mt-1 w-full rounded-md border p-2 text-sm" /></label><Save>Save blocked permit</Save></form><Register empty="No permit readiness records." items={records.map((r) => <article key={r.id} className="rounded-lg border p-4"><div className="flex justify-between gap-3"><div><div className="text-xs font-semibold text-brand-gold-dark">{detail(r,"type")} · {r.work_date}</div><h3 className="font-semibold">{detail(r,"project")}</h3><p className="text-sm text-iron-600">{detail(r,"task")}</p><p className="mt-2 text-xs text-iron-500">Supervisor: {detail(r,"supervisor")} · Expires: {detail(r,"expires") || "Not set"}</p></div><Status value={r.status} /></div><p className="mt-3 rounded-md bg-iron-50 p-3 text-sm">{detail(r,"controls")}</p><div className="mt-3 flex gap-2"><Small onClick={() => void transition(r,"at_risk","Record the review evidence and remaining risk.")}>Mark at risk</Small><Small dark onClick={() => void transition(r,"ready","Record the field verification that supports release.")}>Verify ready</Small></div></article>)} /></Grid>; }

function ActionView({records,create,transition}:{records:FieldRecord[];create:Create;transition:Transition}) { return <Grid><form onSubmit={(e) => void create(e,"corrective_action","finding")} className="space-y-3 rounded-xl border bg-white p-6"><h2 className="font-semibold">Create corrective action</h2>{[["finding","Finding"],["risk","Risk / consequence"],["immediate","Immediate control"],["permanent","Permanent action"],["owner","Action owner"]].map(([name,placeholder]) => <Input key={name} name={name} placeholder={placeholder} />)}<label className="block text-xs font-semibold text-iron-500">Due date<input required name="due" type="date" className="mt-1 w-full rounded-md border p-2 text-sm" /></label><Save>Save action</Save></form><Register empty="No corrective actions." items={records.map((r) => <article key={r.id} className="rounded-lg border p-4"><div className="flex justify-between"><div><h3 className="font-semibold">{detail(r,"finding")}</h3><p className="text-sm text-iron-500">Owner: {detail(r,"owner")} · Due: {detail(r,"due")}</p></div><Status value={r.status} /></div><p className="mt-3 text-sm"><b>Immediate:</b> {detail(r,"immediate")}</p><p className="mt-1 text-sm"><b>Permanent:</b> {detail(r,"permanent")}</p><div className="mt-3 flex gap-2"><Small onClick={() => void transition(r,"verification","Record completion evidence for management verification.")}>Submit evidence</Small><Small dark onClick={() => void transition(r,"closed","Record how effectiveness was verified before closure.")}>Verify and close</Small></div></article>)} /></Grid>; }

function EmergencyView({records,create}:{records:FieldRecord[];create:Create}) { return <Grid><form onSubmit={(e) => void create(e,"emergency_action_card","project")} className="space-y-3 rounded-xl border bg-white p-6"><h2 className="font-semibold">Create emergency action card</h2>{[["project","Project"],["address","Site address / access point"],["muster","Muster point"],["firstAid","First aid location and attendant"],["emergencyLead","Emergency lead and contact"],["rescue","Rescue / evacuation method"]].map(([name,placeholder]) => <Input key={name} name={name} placeholder={placeholder} />)}<Save>Save emergency card</Save></form><Register empty="No emergency cards." items={records.map((r) => <article key={r.id} className="rounded-lg border border-red-200 bg-red-50 p-5"><div className="flex items-center gap-2"><Radio className="text-red-700" /><h3 className="font-semibold text-red-950">{detail(r,"project")}</h3></div><dl className="mt-4 grid gap-2 text-sm"><div><b>Address/access:</b> {detail(r,"address")}</div><div><b>Muster point:</b> {detail(r,"muster")}</div><div><b>First aid:</b> {detail(r,"firstAid")}</div><div><b>Emergency lead:</b> {detail(r,"emergencyLead")}</div><div><b>Rescue/evacuation:</b> {detail(r,"rescue")}</div></dl><p className="mt-3 text-xs text-red-800">Created {r.work_date}. Confirm with the crew and replace when conditions change.</p></article>)} /></Grid>; }

function detail(record:FieldRecord,key:string) { const value=record.details[key]; return typeof value === "string" ? value : ""; }
function message(value:unknown) { return value instanceof Error ? value.message : "Unable to complete the safety operation."; }
function Grid({children}:{children:ReactNode}) { return <div className="grid gap-6 xl:grid-cols-[390px_1fr]">{children}</div>; }
function Input(props:{name:string;placeholder:string}) { return <input required {...props} className="w-full rounded-md border p-2 text-sm" />; }
function Area(props:{name:string;placeholder:string}) { return <textarea required {...props} className="h-24 w-full rounded-md border p-2 text-sm" />; }
function Save({children}:{children:ReactNode}) { return <button className="w-full rounded-md bg-brand-gold p-2 text-sm font-semibold">{children}</button>; }
function Small({children,dark=false,onClick}:{children:ReactNode;dark?:boolean;onClick:()=>void}) { return <button onClick={onClick} className={`min-h-11 rounded-md px-3 text-xs font-semibold ${dark ? "bg-iron-950 text-white" : "border"}`}>{children}</button>; }
function Metric({label,value,icon}:{label:string;value:number;icon:ReactNode}) { return <article className="rounded-xl border bg-white p-5"><div className="flex items-center justify-between text-sm font-medium text-iron-500"><span>{label}</span>{icon}</div><div className="mt-2 text-3xl font-semibold">{value}</div></article>; }
function Status({value}:{value:string}) { return <span className={`h-fit rounded-full px-2 py-1 text-xs font-semibold ${value === "ready" || value === "closed" ? "bg-emerald-100 text-emerald-800" : value === "at_risk" || value === "verification" ? "bg-amber-100 text-amber-800" : "bg-red-100 text-red-800"}`}>{value.replace("_"," ")}</span>; }
function Register({items,empty}:{items:ReactNode[];empty:string}) { return <section className="rounded-xl border bg-white p-6"><div className="flex items-center gap-2"><ClipboardList className="text-brand-gold-dark" /><h2 className="font-semibold">Register</h2></div><div className="mt-4 space-y-3">{items.length ? items : <p className="rounded-md bg-iron-50 p-4 text-sm text-iron-500">{empty}</p>}</div></section>; }
