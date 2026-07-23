import { FormEvent, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, ClipboardList, Radio, ShieldAlert, Siren } from "lucide-react";

type PermitStatus = "Blocked" | "At risk" | "Ready";
type Permit = { id: string; type: string; project: string; task: string; supervisor: string; status: PermitStatus; controls: string; expires: string; created: string };
type Action = { id: string; finding: string; risk: string; immediate: string; permanent: string; owner: string; due: string; status: "Open" | "Verification" | "Closed"; evidence: string };
type EmergencyCard = { id: string; project: string; address: string; muster: string; firstAid: string; emergencyLead: string; rescue: string; reviewed: string };

function useLocalState<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(() => {
    try { const stored = localStorage.getItem(key); return stored ? JSON.parse(stored) as T : initial; } catch { return initial; }
  });
  const save = (next: T) => { setValue(next); localStorage.setItem(key, JSON.stringify(next)); };
  return [value, save] as const;
}

export function SafetyOperationsPage() {
  const [permits, setPermits] = useLocalState<Permit[]>("ihos-safety-permits", []);
  const [actions, setActions] = useLocalState<Action[]>("ihos-safety-actions", []);
  const [cards, setCards] = useLocalState<EmergencyCard[]>("ihos-emergency-cards", []);
  const [view, setView] = useState<"permits" | "actions" | "emergency">("permits");

  const blocked = permits.filter((p) => p.status === "Blocked").length;
  const overdue = useMemo(() => actions.filter((a) => a.status !== "Closed" && a.due && new Date(a.due).getTime() < Date.now()).length, [actions]);

  function addPermit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget);
    const permit: Permit = { id: crypto.randomUUID(), type: String(data.get("type")), project: String(data.get("project")), task: String(data.get("task")), supervisor: String(data.get("supervisor")), status: String(data.get("status")) as PermitStatus, controls: String(data.get("controls")), expires: String(data.get("expires")), created: new Date().toISOString().slice(0, 10) };
    setPermits([permit, ...permits]); event.currentTarget.reset();
  }

  function addAction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget);
    const action: Action = { id: crypto.randomUUID(), finding: String(data.get("finding")), risk: String(data.get("risk")), immediate: String(data.get("immediate")), permanent: String(data.get("permanent")), owner: String(data.get("owner")), due: String(data.get("due")), status: "Open", evidence: "" };
    setActions([action, ...actions]); event.currentTarget.reset();
  }

  function addCard(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget);
    const card: EmergencyCard = { id: crypto.randomUUID(), project: String(data.get("project")), address: String(data.get("address")), muster: String(data.get("muster")), firstAid: String(data.get("firstAid")), emergencyLead: String(data.get("emergencyLead")), rescue: String(data.get("rescue")), reviewed: new Date().toISOString().slice(0, 10) };
    setCards([card, ...cards]); event.currentTarget.reset();
  }

  return <section className="space-y-6">
    <header className="ihos-brand-surface rounded-xl border border-brand-gold/30 p-6 text-white shadow-brand"><div className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-gold">Build 221</div><h1 className="mt-2 text-3xl font-semibold text-brand-silver">Safety Operations Control</h1><p className="mt-2 max-w-3xl text-sm text-iron-100">Permit readiness, corrective-action verification and project emergency action cards.</p></header>
    <div className="grid gap-4 md:grid-cols-3"><Metric label="Blocked permits" value={blocked} icon={<ShieldAlert />} /><Metric label="Overdue actions" value={overdue} icon={<AlertTriangle />} /><Metric label="Emergency cards" value={cards.length} icon={<Siren />} /></div>
    <nav className="flex gap-2 overflow-x-auto rounded-xl border border-iron-100 bg-white p-2">{[["permits","High-risk permits"],["actions","Corrective actions"],["emergency","Emergency cards"]].map(([key,label]) => <button key={key} onClick={() => setView(key as typeof view)} className={`rounded-md px-4 py-2 text-sm font-semibold ${view === key ? "bg-brand-gold text-brand-black" : "text-iron-600"}`}>{label}</button>)}</nav>

    {view === "permits" && <div className="grid gap-6 xl:grid-cols-[390px_1fr]"><form onSubmit={addPermit} className="space-y-3 rounded-xl border bg-white p-6"><h2 className="font-semibold">Create permit readiness record</h2><select name="type" className="w-full rounded-md border p-2 text-sm"><option>Ground Disturbance</option><option>Confined Space</option><option>Lockout / Energy Isolation</option><option>Critical Lift</option><option>Traffic Control</option></select><input required name="project" placeholder="Project / location" className="w-full rounded-md border p-2 text-sm" /><textarea required name="task" placeholder="Task and work limits" className="h-20 w-full rounded-md border p-2 text-sm" /><input required name="supervisor" placeholder="Responsible supervisor" className="w-full rounded-md border p-2 text-sm" /><textarea required name="controls" placeholder="Controls and verification evidence required" className="h-24 w-full rounded-md border p-2 text-sm" /><label className="block text-xs font-semibold text-iron-500">Permit expiry<input name="expires" type="datetime-local" className="mt-1 w-full rounded-md border p-2 text-sm" /></label><select name="status" className="w-full rounded-md border p-2 text-sm"><option>Blocked</option><option>At risk</option><option>Ready</option></select><button className="w-full rounded-md bg-brand-gold p-2 text-sm font-semibold">Save permit</button></form><Register empty="No permit readiness records." items={permits.map((p) => <div key={p.id} className="rounded-lg border p-4"><div className="flex justify-between gap-3"><div><div className="text-xs font-semibold text-brand-gold-dark">{p.type} · {p.created}</div><h3 className="font-semibold">{p.project}</h3><p className="text-sm text-iron-600">{p.task}</p><p className="mt-2 text-xs text-iron-500">Supervisor: {p.supervisor} · Expires: {p.expires || "Not set"}</p></div><Status value={p.status} /></div><p className="mt-3 rounded-md bg-iron-50 p-3 text-sm">{p.controls}</p><div className="mt-3 flex gap-2"><button onClick={() => setPermits(permits.map((x) => x.id === p.id ? {...x,status:"At risk"} : x))} className="rounded-md border px-3 py-1 text-xs font-semibold">At risk</button><button onClick={() => setPermits(permits.map((x) => x.id === p.id ? {...x,status:"Ready"} : x))} className="rounded-md bg-iron-950 px-3 py-1 text-xs font-semibold text-white">Verify ready</button></div></div>)} /></div>}

    {view === "actions" && <div className="grid gap-6 xl:grid-cols-[390px_1fr]"><form onSubmit={addAction} className="space-y-3 rounded-xl border bg-white p-6"><h2 className="font-semibold">Create corrective action</h2>{[["finding","Finding"],["risk","Risk / consequence"],["immediate","Immediate control"],["permanent","Permanent action"],["owner","Action owner"]].map(([name,placeholder]) => <input key={name} required name={name} placeholder={placeholder} className="w-full rounded-md border p-2 text-sm" />)}<label className="block text-xs font-semibold text-iron-500">Due date<input required name="due" type="date" className="mt-1 w-full rounded-md border p-2 text-sm" /></label><button className="w-full rounded-md bg-brand-gold p-2 text-sm font-semibold">Save action</button></form><Register empty="No corrective actions." items={actions.map((a) => <div key={a.id} className="rounded-lg border p-4"><div className="flex justify-between"><div><h3 className="font-semibold">{a.finding}</h3><p className="text-sm text-iron-500">Owner: {a.owner} · Due: {a.due}</p></div><span className="text-xs font-semibold">{a.status}</span></div><p className="mt-3 text-sm"><b>Immediate:</b> {a.immediate}</p><p className="mt-1 text-sm"><b>Permanent:</b> {a.permanent}</p><input defaultValue={a.evidence} onBlur={(e) => setActions(actions.map((x) => x.id === a.id ? {...x,evidence:e.target.value,status:e.target.value ? "Verification" : "Open"} : x))} placeholder="Verification evidence" className="mt-3 w-full rounded-md border p-2 text-sm" /><button disabled={!a.evidence} onClick={() => setActions(actions.map((x) => x.id === a.id ? {...x,status:"Closed"} : x))} className="mt-2 rounded-md bg-iron-950 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40">Verify effective and close</button></div>)} /></div>}

    {view === "emergency" && <div className="grid gap-6 xl:grid-cols-[390px_1fr]"><form onSubmit={addCard} className="space-y-3 rounded-xl border bg-white p-6"><h2 className="font-semibold">Create emergency action card</h2>{[["project","Project"],["address","Site address / access point"],["muster","Muster point"],["firstAid","First aid location and attendant"],["emergencyLead","Emergency lead and contact"],["rescue","Rescue / evacuation method"]].map(([name,placeholder]) => <input key={name} required name={name} placeholder={placeholder} className="w-full rounded-md border p-2 text-sm" />)}<button className="w-full rounded-md bg-brand-gold p-2 text-sm font-semibold">Save emergency card</button></form><Register empty="No emergency cards." items={cards.map((c) => <div key={c.id} className="rounded-lg border border-red-200 bg-red-50 p-5"><div className="flex items-center gap-2"><Radio className="text-red-700" /><h3 className="font-semibold text-red-950">{c.project}</h3></div><dl className="mt-4 grid gap-2 text-sm"><div><b>Address/access:</b> {c.address}</div><div><b>Muster point:</b> {c.muster}</div><div><b>First aid:</b> {c.firstAid}</div><div><b>Emergency lead:</b> {c.emergencyLead}</div><div><b>Rescue/evacuation:</b> {c.rescue}</div></dl><p className="mt-3 text-xs text-red-800">Reviewed {c.reviewed}. Confirm this information with the crew and update when conditions change.</p></div>)} /></div>}
  </section>;
}

function Metric({label,value,icon}:{label:string;value:number;icon:React.ReactNode}) { return <article className="rounded-xl border bg-white p-5"><div className="flex items-center justify-between text-sm font-medium text-iron-500"><span>{label}</span>{icon}</div><div className="mt-2 text-3xl font-semibold">{value}</div></article>; }
function Status({value}:{value:PermitStatus}) { return <span className={`h-fit rounded-full px-2 py-1 text-xs font-semibold ${value === "Ready" ? "bg-emerald-100 text-emerald-800" : value === "At risk" ? "bg-amber-100 text-amber-800" : "bg-red-100 text-red-800"}`}>{value}</span>; }
function Register({items,empty}:{items:React.ReactNode[];empty:string}) { return <section className="rounded-xl border bg-white p-6"><div className="flex items-center gap-2"><ClipboardList className="text-brand-gold-dark" /><h2 className="font-semibold">Register</h2></div><div className="mt-4 space-y-3">{items.length ? items : <p className="rounded-md bg-iron-50 p-4 text-sm text-iron-500">{empty}</p>}</div></section>; }
