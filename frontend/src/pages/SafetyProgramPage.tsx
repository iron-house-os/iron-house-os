import {
  AlertTriangle,
  BarChart3,
  BookOpenCheck,
  BrainCircuit,
  CheckCircle2,
  ClipboardCheck,
  FileWarning,
  GraduationCap,
  HardHat,
  Plus,
  QrCode,
  Search,
  ShieldCheck,
  Siren,
  Sparkles,
  Users,
  Wrench,
} from "lucide-react";
import { FormEvent, useMemo, useState } from "react";

const SAFETY_PROGRAM_URL =
  "https://docs.google.com/document/d/1ApKQs4xIR8axW0lIaeqqATDVaZWs1jvSzaZwYK6wUNw/edit?usp=drivesdk";

const tabs = ["Overview", "Manual & SWPs", "Field Forms", "People & Compliance", "Reporting", "Safety Intelligence"] as const;
type Tab = (typeof tabs)[number];
type SafetyRecord = { id: string; type: string; title: string; project: string; owner: string; status: string; created: string; risk: string };
type TrainingRecord = { id: string; worker: string; credential: string; expiry: string; status: string };

const procedures = [
  { code: "SWP-001", title: "Excavation and Trenching", category: "Earthworks", status: "Controlled" },
  { code: "SWP-002", title: "Ground Disturbance and Utility Locating", category: "Utilities", status: "Controlled" },
  { code: "SWP-003", title: "Mobile Equipment and Spotters", category: "Equipment", status: "Controlled" },
  { code: "SWP-004", title: "Traffic Control and Public Interface", category: "Roadwork", status: "Controlled" },
  { code: "SWP-005", title: "Confined Space Entry", category: "High Risk", status: "Draft review" },
  { code: "SWP-006", title: "Lockout and Energy Isolation", category: "High Risk", status: "Draft review" },
  { code: "SWP-007", title: "Silica Exposure Control", category: "Occupational Health", status: "Controlled" },
  { code: "SWP-008", title: "Lifting, Rigging and Suspended Loads", category: "Equipment", status: "Controlled" },
];

const formTypes = ["FLHA", "Toolbox Talk", "Equipment Inspection", "Incident / Near Miss", "Corrective Action", "Ground Disturbance Permit", "Confined Space Permit", "First Aid Record"];

const hazardLibrary: Record<string, string[]> = {
  excavation: ["Underground utilities", "Cave-in or ground collapse", "Mobile equipment interaction", "Access and egress", "Water accumulation"],
  trenching: ["Cave-in or ground collapse", "Spoil pile surcharge", "Atmospheric hazard", "Falling material", "Restricted access"],
  pipe: ["Suspended loads", "Pinch and crush points", "Unstable trench conditions", "Manual handling", "Stored energy"],
  paving: ["Traffic exposure", "Hot materials", "Backing equipment", "Heat stress", "Public interface"],
  concrete: ["Silica exposure", "Chemical burns", "Formwork failure", "Pump hose movement", "Mobile equipment"],
  default: ["Changing site conditions", "Mobile equipment", "Public or worker interface", "Weather", "Communication failure"],
};

function useStoredState<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(() => {
    try {
      const stored = localStorage.getItem(key);
      return stored ? (JSON.parse(stored) as T) : initial;
    } catch {
      return initial;
    }
  });
  const save = (next: T) => {
    setValue(next);
    localStorage.setItem(key, JSON.stringify(next));
  };
  return [value, save] as const;
}

function StatCard({ label, value, note, icon: Icon }: { label: string; value: string | number; note: string; icon: typeof ShieldCheck }) {
  return (
    <article className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between"><span className="text-sm font-medium text-iron-500">{label}</span><Icon className="h-5 w-5 text-brand-gold-dark" /></div>
      <div className="mt-3 text-3xl font-semibold text-iron-950">{value}</div>
      <p className="mt-1 text-xs text-iron-500">{note}</p>
    </article>
  );
}

export function SafetyProgramPage() {
  const [activeTab, setActiveTab] = useState<Tab>("Overview");
  const [records, setRecords] = useStoredState<SafetyRecord[]>("ihos-safety-records", []);
  const [training, setTraining] = useStoredState<TrainingRecord[]>("ihos-safety-training", []);
  const [search, setSearch] = useState("");
  const [task, setTask] = useState("");
  const [project, setProject] = useState("");
  const [generated, setGenerated] = useState<string[]>([]);

  const filteredProcedures = procedures.filter((item) => `${item.code} ${item.title} ${item.category}`.toLowerCase().includes(search.toLowerCase()));
  const openActions = records.filter((record) => record.status !== "Complete").length;
  const incidents = records.filter((record) => record.type === "Incident / Near Miss").length;
  const expiring = useMemo(() => training.filter((item) => item.status !== "Current").length, [training]);

  function addRecord(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const next: SafetyRecord = {
      id: crypto.randomUUID(),
      type: String(data.get("type")),
      title: String(data.get("title")),
      project: String(data.get("project")),
      owner: String(data.get("owner")),
      status: "Open",
      created: new Date().toISOString().slice(0, 10),
      risk: String(data.get("risk")),
    };
    setRecords([next, ...records]);
    event.currentTarget.reset();
  }

  function addTraining(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const expiry = String(data.get("expiry"));
    const days = expiry ? Math.ceil((new Date(expiry).getTime() - Date.now()) / 86400000) : 9999;
    const status = days < 0 ? "Expired" : days <= 60 ? "Expiring" : "Current";
    setTraining([{ id: crypto.randomUUID(), worker: String(data.get("worker")), credential: String(data.get("credential")), expiry, status }, ...training]);
    event.currentTarget.reset();
  }

  function generateHazards() {
    const key = Object.keys(hazardLibrary).find((word) => task.toLowerCase().includes(word)) ?? "default";
    setGenerated(hazardLibrary[key]);
  }

  return (
    <section className="space-y-6">
      <div className="ihos-brand-surface overflow-hidden rounded-xl border border-brand-gold/30 px-6 py-6 text-white shadow-brand">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="grid h-14 w-14 place-items-center rounded-xl border border-brand-gold/40 bg-white/10 text-brand-gold"><HardHat /></div>
            <div><div className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-gold">Build 221</div><h1 className="mt-2 text-3xl font-semibold text-brand-silver">Safety Management System</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-iron-100">Controlled safety documents, field records, competency, corrective actions, analytics and intelligent hazard planning.</p></div>
          </div>
          <a href={SAFETY_PROGRAM_URL} target="_blank" rel="noreferrer" className="rounded-md bg-brand-gold px-4 py-2 text-sm font-semibold text-brand-black">Open Safety Manual</a>
        </div>
      </div>

      <nav className="flex gap-2 overflow-x-auto rounded-xl border border-iron-100 bg-white p-2 shadow-sm">
        {tabs.map((tab) => <button key={tab} onClick={() => setActiveTab(tab)} className={`whitespace-nowrap rounded-md px-4 py-2 text-sm font-semibold ${activeTab === tab ? "bg-brand-gold text-brand-black" : "text-iron-600 hover:bg-iron-50"}`}>{tab}</button>)}
      </nav>

      {activeTab === "Overview" && <>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Open safety records" value={openActions} note="Requires field or management closure" icon={ClipboardCheck} />
          <StatCard label="Incident / near miss" value={incidents} note="Recorded in this browser" icon={FileWarning} />
          <StatCard label="Training alerts" value={expiring} note="Expired or within 60 days" icon={GraduationCap} />
          <StatCard label="Controlled procedures" value={procedures.filter((p) => p.status === "Controlled").length} note={`${procedures.length} procedures indexed`} icon={ShieldCheck} />
        </div>
        <section className="grid gap-4 lg:grid-cols-2">
          <article className="rounded-xl border border-iron-100 bg-white p-6 shadow-sm"><h2 className="font-semibold text-iron-950">Implementation status</h2><div className="mt-4 space-y-3">{[
            ["Phase 1 — Core safety hub", "Complete"], ["Phase 2 — Field forms", "Complete"], ["Phase 3 — People and compliance", "Complete"], ["Phase 4 — Reporting and field deployment", "Core complete"], ["Safety Intelligence", "Initial engine active"],
          ].map(([name, status]) => <div key={name} className="flex items-center justify-between rounded-md border border-iron-100 p-3"><span className="text-sm font-medium">{name}</span><span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">{status}</span></div>)}</div></article>
          <article className="rounded-xl border border-brand-gold/30 bg-white p-6 shadow-sm"><h2 className="font-semibold text-iron-950">Field release controls</h2><p className="mt-2 text-sm leading-6 text-iron-600">Digital records support planning and evidence, but do not replace field verification. The responsible supervisor must confirm actual conditions, qualifications, inspections, permits, emergency arrangements and stop-work triggers before work proceeds.</p><div className="mt-4 grid gap-2 text-sm"><div className="rounded-md bg-red-50 p-3"><b>Blocked:</b> critical control or evidence missing.</div><div className="rounded-md bg-amber-50 p-3"><b>At risk:</b> work may proceed only with dated corrective action and enhanced supervision.</div><div className="rounded-md bg-emerald-50 p-3"><b>Ready:</b> required controls and evidence verified for planned conditions.</div></div></article>
        </section>
      </>}

      {activeTab === "Manual & SWPs" && <section className="space-y-4 rounded-xl border border-iron-100 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-semibold text-iron-950">Controlled manual and SWP library</h2><p className="text-sm text-iron-500">Revision 1.2 · July 23, 2026</p></div><div className="relative"><Search className="absolute left-3 top-2.5 h-4 w-4 text-iron-400" /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search procedures" className="rounded-md border border-iron-200 py-2 pl-9 pr-3 text-sm" /></div></div>
        <div className="grid gap-3 md:grid-cols-2">{filteredProcedures.map((item) => <article key={item.code} className="rounded-lg border border-iron-100 p-4"><div className="flex justify-between gap-3"><div><div className="text-xs font-semibold text-brand-gold-dark">{item.code} · {item.category}</div><h3 className="mt-1 font-semibold">{item.title}</h3></div><span className={`h-fit rounded-full px-2 py-1 text-xs font-semibold ${item.status === "Controlled" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>{item.status}</span></div><button className="mt-4 text-sm font-semibold text-brand-gold-dark">Open procedure</button></article>)}</div>
      </section>}

      {activeTab === "Field Forms" && <section className="grid gap-6 xl:grid-cols-[380px_1fr]">
        <form onSubmit={addRecord} className="space-y-3 rounded-xl border border-iron-100 bg-white p-6 shadow-sm"><div className="flex items-center gap-2"><Plus className="h-5 w-5 text-brand-gold-dark" /><h2 className="font-semibold">Create safety record</h2></div><select name="type" className="w-full rounded-md border border-iron-200 p-2 text-sm">{formTypes.map((type) => <option key={type}>{type}</option>)}</select><input required name="title" placeholder="Task, event or action" className="w-full rounded-md border border-iron-200 p-2 text-sm" /><input name="project" placeholder="Project / location" className="w-full rounded-md border border-iron-200 p-2 text-sm" /><input required name="owner" placeholder="Responsible person" className="w-full rounded-md border border-iron-200 p-2 text-sm" /><select name="risk" className="w-full rounded-md border border-iron-200 p-2 text-sm"><option>Normal</option><option>High</option><option>Critical</option></select><button className="w-full rounded-md bg-brand-gold px-4 py-2 text-sm font-semibold text-brand-black">Save record</button></form>
        <article className="rounded-xl border border-iron-100 bg-white p-6 shadow-sm"><h2 className="font-semibold">Field record register</h2><div className="mt-4 space-y-3">{records.length === 0 ? <p className="rounded-md bg-iron-50 p-4 text-sm text-iron-500">No records yet. Create the first FLHA, inspection, permit, incident or corrective action.</p> : records.map((record) => <div key={record.id} className="rounded-lg border border-iron-100 p-4"><div className="flex flex-wrap justify-between gap-3"><div><div className="text-xs font-semibold text-brand-gold-dark">{record.type} · {record.created}</div><h3 className="mt-1 font-semibold">{record.title}</h3><p className="mt-1 text-sm text-iron-500">{record.project || "Company"} · Owner: {record.owner}</p></div><div className="flex gap-2"><span className="h-fit rounded-full bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-800">{record.status}</span><button onClick={() => setRecords(records.map((r) => r.id === record.id ? { ...r, status: "Complete" } : r))} className="h-fit rounded-md border px-2 py-1 text-xs font-semibold">Close</button></div></div></div>)}</div></article>
      </section>}

      {activeTab === "People & Compliance" && <section className="grid gap-6 xl:grid-cols-[380px_1fr]">
        <form onSubmit={addTraining} className="space-y-3 rounded-xl border border-iron-100 bg-white p-6 shadow-sm"><div className="flex items-center gap-2"><Users className="h-5 w-5 text-brand-gold-dark" /><h2 className="font-semibold">Add competency record</h2></div><input required name="worker" placeholder="Worker name" className="w-full rounded-md border border-iron-200 p-2 text-sm" /><input required name="credential" placeholder="Ticket, orientation or competency" className="w-full rounded-md border border-iron-200 p-2 text-sm" /><label className="block text-xs font-semibold text-iron-500">Expiry date<input name="expiry" type="date" className="mt-1 w-full rounded-md border border-iron-200 p-2 text-sm" /></label><button className="w-full rounded-md bg-brand-gold px-4 py-2 text-sm font-semibold text-brand-black">Save competency</button></form>
        <article className="rounded-xl border border-iron-100 bg-white p-6 shadow-sm"><h2 className="font-semibold">Training and competency matrix</h2><div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b text-xs uppercase text-iron-500"><th className="p-2">Worker</th><th className="p-2">Credential</th><th className="p-2">Expiry</th><th className="p-2">Status</th></tr></thead><tbody>{training.map((item) => <tr key={item.id} className="border-b"><td className="p-2 font-medium">{item.worker}</td><td className="p-2">{item.credential}</td><td className="p-2">{item.expiry || "No expiry"}</td><td className="p-2"><span className={`rounded-full px-2 py-1 text-xs font-semibold ${item.status === "Current" ? "bg-emerald-100 text-emerald-800" : item.status === "Expiring" ? "bg-amber-100 text-amber-800" : "bg-red-100 text-red-800"}`}>{item.status}</span></td></tr>)}</tbody></table>{training.length === 0 && <p className="mt-4 rounded-md bg-iron-50 p-4 text-sm text-iron-500">No competency records entered.</p>}</div></article>
      </section>}

      {activeTab === "Reporting" && <section className="space-y-5">
        <div className="grid gap-4 md:grid-cols-3"><StatCard label="Total records" value={records.length} note="All field and management records" icon={BarChart3} /><StatCard label="Closed records" value={records.filter((r) => r.status === "Complete").length} note="Closure evidence still requires review" icon={CheckCircle2} /><StatCard label="Critical records" value={records.filter((r) => r.risk === "Critical").length} note="Immediate management attention" icon={Siren} /></div>
        <article className="rounded-xl border border-iron-100 bg-white p-6 shadow-sm"><h2 className="font-semibold">Safety analytics</h2><div className="mt-5 grid gap-4 md:grid-cols-2">{formTypes.slice(0, 6).map((type) => { const count = records.filter((r) => r.type === type).length; const width = records.length ? Math.max(5, Math.round((count / records.length) * 100)) : 0; return <div key={type}><div className="flex justify-between text-sm"><span>{type}</span><b>{count}</b></div><div className="mt-2 h-2 rounded-full bg-iron-100"><div className="h-2 rounded-full bg-brand-gold" style={{ width: `${width}%` }} /></div></div>; })}</div><p className="mt-5 text-xs text-iron-500">Analytics are based on records stored in this browser. Server-backed company reporting and audit exports remain a deployment integration item.</p></article>
        <article className="rounded-xl border border-iron-100 bg-white p-6 shadow-sm"><div className="flex items-center gap-3"><QrCode className="text-brand-gold-dark" /><div><h2 className="font-semibold">Field deployment</h2><p className="text-sm text-iron-500">QR-ready links can be generated for equipment and procedure pages after permanent production URLs and asset identifiers are confirmed.</p></div></div></article>
      </section>}

      {activeTab === "Safety Intelligence" && <section className="grid gap-6 xl:grid-cols-[420px_1fr]">
        <article className="rounded-xl border border-brand-gold/40 bg-white p-6 shadow-sm"><div className="flex items-center gap-3"><BrainCircuit className="h-6 w-6 text-brand-gold-dark" /><div><h2 className="font-semibold">Intelligent hazard planner</h2><p className="text-sm text-iron-500">Draft planning aid — supervisor verification required.</p></div></div><div className="mt-5 space-y-3"><input value={project} onChange={(e) => setProject(e.target.value)} placeholder="Project / location" className="w-full rounded-md border border-iron-200 p-2 text-sm" /><textarea value={task} onChange={(e) => setTask(e.target.value)} placeholder="Describe the work: e.g. excavate a 3 m trench and install storm pipe beside live traffic" className="h-32 w-full rounded-md border border-iron-200 p-2 text-sm" /><button onClick={generateHazards} disabled={!task.trim()} className="flex w-full items-center justify-center gap-2 rounded-md bg-brand-gold px-4 py-2 text-sm font-semibold text-brand-black disabled:opacity-50"><Sparkles className="h-4 w-4" />Generate hazard draft</button></div></article>
        <article className="rounded-xl border border-iron-100 bg-white p-6 shadow-sm"><h2 className="font-semibold">Draft hazard and control prompt</h2>{generated.length === 0 ? <p className="mt-4 rounded-md bg-iron-50 p-4 text-sm text-iron-500">Describe a task to generate an initial hazard list.</p> : <div className="mt-4 space-y-3"><div className="rounded-md border border-brand-gold/30 bg-brand-gold/10 p-3 text-sm"><b>{project || "Unassigned project"}</b><br />{task}</div>{generated.map((hazard) => <div key={hazard} className="flex gap-3 rounded-md border border-iron-100 p-3"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" /><div><div className="text-sm font-semibold">{hazard}</div><p className="mt-1 text-xs text-iron-500">Apply the hierarchy of controls, assign a responsible person, define verification evidence and confirm emergency / stop-work triggers.</p></div></div>)}<div className="rounded-md bg-red-50 p-3 text-xs leading-5 text-red-800"><b>Human review gate:</b> This draft is not a legal opinion, engineered procedure, permit, FLHA approval or authorization to proceed. Confirm current WorkSafeBC requirements, project documents, manufacturer instructions and actual field conditions.</div></div>}</article>
      </section>}
    </section>
  );
}
