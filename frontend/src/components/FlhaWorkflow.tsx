import { FormEvent, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, FileDown, Plus, RotateCcw, ShieldCheck, Trash2 } from "lucide-react";

import { fieldOperationsApi, FieldOperationsBootstrap, FieldRecord } from "../api/fieldOperations";
import { mediaApi } from "../api/media";
import { UniversalPhotoField } from "./UniversalPhotoField";

type Answer = "yes" | "no" | "na";
type TaskRow = { id: string; task: string; hazard: string; control: string; control_type: string; responsible_person: string; critical: boolean; control_accepted: boolean; evidence_required: boolean; evidence: string };
const screenings = [
  ["first_aid_equipment", "First aid equipment"], ["overhead_hazards", "Overhead hazards"],
  ["underground_utilities_locates", "Underground utilities / current locates"], ["mobile_equipment", "Mobile equipment"],
  ["confined_space", "Confined space"], ["excavation_protection_access", "Excavation sloping / shoring / safe access"],
  ["additional_ppe", "Additional PPE"], ["traffic_control", "Traffic control"],
  ["subcontractors", "Subcontractors"], ["basic_ppe_review", "Basic PPE review"],
] as const;
const hierarchy = [["elimination", "Elimination"], ["substitution", "Substitution"], ["engineering", "Engineering"], ["administrative", "Administrative"], ["ppe", "PPE"]];
const presets: Record<string, Omit<TaskRow, "id">> = {
  excavation: { task: "Excavation and trench access", hazard: "Ground collapse, utilities or unsafe access", control: "Confirm locates; inspect protective system and ladder before entry", control_type: "engineering", responsible_person: "", critical: true, control_accepted: false, evidence_required: true, evidence: "" },
  equipment: { task: "Mobile equipment operation", hazard: "Worker / equipment interaction", control: "Separate travel path; use spotter and positive communication", control_type: "engineering", responsible_person: "", critical: true, control_accepted: false, evidence_required: false, evidence: "" },
  traffic: { task: "Work beside public traffic", hazard: "Vehicle intrusion", control: "Apply approved traffic-control setup and verify escape route", control_type: "administrative", responsible_person: "", critical: true, control_accepted: false, evidence_required: true, evidence: "" },
};
const blankRow = (): TaskRow => ({ id: crypto.randomUUID(), task: "", hazard: "", control: "", control_type: "engineering", responsible_person: "", critical: false, control_accepted: false, evidence_required: false, evidence: "" });
const today = () => new Date().toISOString().slice(0, 10);

function Field({ label, value, onChange, required = false, readOnly = false }: { label: string; value: string; onChange: (value: string) => void; required?: boolean; readOnly?: boolean }) {
  return <label className="grid gap-1 text-sm font-medium text-iron-700"><span>{label}{required ? " *" : ""}</span><input required={required} readOnly={readOnly} value={value} onChange={(event) => onChange(event.target.value)} className="min-h-11 rounded-md border border-iron-200 px-3 py-2 read-only:bg-iron-50" /></label>;
}

export function FlhaWorkflow({ data, onSaved, onError }: { data: FieldOperationsBootstrap; onSaved: () => Promise<void>; onError: (value: string | null) => void }) {
  const foreperson = data.employees.find((employee) => employee.portal_role === "foreman");
  const previous = data.records.find((record) => record.record_type === "daily_hazard_assessment");
  const [projectId, setProjectId] = useState(previous?.project_id ?? data.projects[0]?.id ?? "");
  const [site, setSite] = useState(String(previous?.details.site_location ?? ""));
  const [supervisor, setSupervisor] = useState(foreperson ? `${foreperson.first_name} ${foreperson.last_name}` : "");
  const [firstAid, setFirstAid] = useState(String(previous?.details.first_aid_attendant ?? ""));
  const [weather, setWeather] = useState(String(previous?.details.weather ?? data.records.find((record) => record.record_type === "weather")?.details.weather ?? ""));
  const [crew, setCrew] = useState<string[]>(() => ((previous?.details.crew as Array<{ employee_id?: string }> | undefined) ?? []).map((entry) => entry.employee_id ?? "").filter(Boolean));
  const [answers, setAnswers] = useState<Record<string, Answer>>({});
  const [rows, setRows] = useState<TaskRow[]>([blankRow()]);
  const [muster, setMuster] = useState("");
  const [firstAidPlan, setFirstAidPlan] = useState("");
  const [communication, setCommunication] = useState("");
  const [stopWork, setStopWork] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [existingDocuments, setExistingDocuments] = useState<string[]>([]);
  const [projectPresets, setProjectPresets] = useState<Record<string, Omit<TaskRow, "id">[][]>>(() => {
    try { return JSON.parse(localStorage.getItem("ihos-flha-project-presets") ?? "{}"); } catch { return {}; }
  });
  const flhas = useMemo(() => data.records.filter((record) => record.record_type === "daily_hazard_assessment"), [data.records]);
  const unresolvedCritical = rows.some((row) => row.critical && (!row.control_accepted || !row.responsible_person || (row.evidence_required && !row.evidence)));
  const draftBlocked = unresolvedCritical || !projectId || !site || !supervisor || !firstAid || !weather || !crew.length || Object.keys(answers).length !== screenings.length || !rows.length || rows.some((row) => !row.task || !row.hazard || !row.control || !row.responsible_person) || !muster || !firstAidPlan || !communication || !stopWork;

  function updateRow(id: string, patch: Partial<TaskRow>) { setRows((current) => current.map((row) => row.id === id ? { ...row, ...patch } : row)); }
  function addPreset(key: string) { setRows((current) => [...current.filter((row) => row.task || row.hazard || row.control), { id: crypto.randomUUID(), ...presets[key] }]); }
  function saveProjectPreset() {
    const savedRows = rows.filter((row) => row.task && row.hazard && row.control).map(({ id: _id, ...row }) => row);
    if (!savedRows.length || !projectId) return;
    const next = { ...projectPresets, [projectId]: [...(projectPresets[projectId] ?? []), savedRows] };
    setProjectPresets(next); localStorage.setItem("ihos-flha-project-presets", JSON.stringify(next));
  }
  function addProjectPreset(index: number) { setRows((projectPresets[projectId]?.[index] ?? []).map((row) => ({ id: crypto.randomUUID(), ...row }))); }

  function editRecord(record: FieldRecord) {
    const details = record.details;
    const emergency = (details.emergency as Record<string, unknown> | undefined) ?? {};
    setEditingId(record.id); setExistingDocuments(record.document_ids); setProjectId(record.project_id ?? "");
    setSite(String(details.site_location ?? "")); setSupervisor(String(details.supervisor ?? ""));
    setFirstAid(String(details.first_aid_attendant ?? "")); setWeather(String(details.weather ?? ""));
    setCrew(((details.crew as Array<{ employee_id?: string }> | undefined) ?? []).map((entry) => entry.employee_id ?? "").filter(Boolean));
    setAnswers((details.screenings as Record<string, Answer> | undefined) ?? {});
    setRows(((details.tasks as Array<Omit<TaskRow, "id">> | undefined) ?? []).map((row) => ({ id: crypto.randomUUID(), ...row })));
    setMuster(String(emergency.muster_point ?? "")); setFirstAidPlan(String(emergency.first_aid ?? ""));
    setCommunication(String(emergency.communication ?? "")); setStopWork(String(emergency.stop_work_triggers ?? ""));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); onError(null);
    try {
      const uploaded = files.length ? await mediaApi.upload({ files, projectId, caption: "FLHA " + site, capturedDate: today(), category: "flha" }) : [];
      const assets = uploaded.map((asset) => asset.original_document_id);
      const details = {
        site_location: site, assessment_time: new Date().toISOString(), supervisor, first_aid_attendant: firstAid,
        crew: crew.map((id) => { const person = data.employees.find((employee) => employee.id === id)!; return { employee_id: id, name: person.first_name + " " + person.last_name }; }),
        weather, screenings: answers, tasks: rows.map(({ id: _id, ...row }) => row),
        emergency: { muster_point: muster, first_aid: firstAidPlan, communication, stop_work_triggers: stopWork },
        source: "Field-entered; responsible person verification required", ai_safety_decision: false,
      };
      const payload = { title: "FLHA — " + site, severity: rows.some((row) => row.critical) ? "critical" : "none", document_ids: [...existingDocuments, ...assets], details };
      const record = editingId
        ? await fieldOperationsApi.updateRecord(editingId, payload)
        : await fieldOperationsApi.createRecord({ record_type: "daily_hazard_assessment", project_id: projectId, work_date: today(), ...payload });
      await Promise.all(uploaded.map((asset) => mediaApi.link(asset.id, "field_record", record.id)));
      setRows([blankRow()]); setAnswers({}); setCrew([]); setFiles([]); setEditingId(null); setExistingDocuments([]); await onSaved();
    } catch (current) { onError(current instanceof Error ? current.message : "Unable to save FLHA."); }
    finally { setSaving(false); }
  }

  return <div className="space-y-5">
    <form onSubmit={submit} className="space-y-5 rounded-xl border border-brand-gold/40 bg-white p-4 shadow-sm sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><div className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-gold-dark">Field level hazard assessment</div><h2 className="mt-1 text-xl font-semibold text-iron-950">Plan, control and acknowledge today’s work</h2><p className="mt-1 text-sm text-iron-600">Field conditions must be verified by the responsible foreperson. Suggestions never mark work safe.</p></div><span className={`rounded-full px-3 py-1 text-xs font-semibold ${draftBlocked ? "bg-red-100 text-red-800" : "bg-emerald-100 text-emerald-800"}`}>{draftBlocked ? "Blocked" : "Draft"}</span></div>

      <section><h3 className="font-semibold text-iron-900">1. Job and crew</h3><div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <label className="grid gap-1 text-sm font-medium text-iron-700"><span>Project / job *</span><select required value={projectId} onChange={(event) => setProjectId(event.target.value)} className="min-h-11 rounded-md border border-iron-200 px-3">{data.projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label>
        <Field label="Site / location" value={site} onChange={setSite} required /><Field label="Date / time" value={new Date().toLocaleString()} onChange={() => undefined} readOnly />
        <Field label="Supervisor / foreperson" value={supervisor} onChange={setSupervisor} required /><Field label="First aid attendant" value={firstAid} onChange={setFirstAid} required /><Field label="Weather / conditions" value={weather} onChange={setWeather} required />
      </div><fieldset className="mt-3 rounded-md bg-iron-50 p-3"><legend className="px-1 text-sm font-semibold">Crew required to review and sign *</legend><div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{data.employees.map((employee) => <label key={employee.id} className="flex min-h-10 items-center gap-2 text-sm"><input type="checkbox" checked={crew.includes(employee.id)} onChange={(event) => setCrew(event.target.checked ? [...crew, employee.id] : crew.filter((id) => id !== employee.id))} />{employee.first_name} {employee.last_name}</label>)}</div></fieldset></section>

      <section><h3 className="font-semibold text-iron-900">2. Fast hazard screening</h3><div className="mt-3 grid gap-2 md:grid-cols-2">{screenings.map(([key, label]) => <div key={key} className="flex items-center justify-between gap-3 rounded-md border border-iron-100 p-3"><span className="text-sm font-medium">{label}</span><div className="flex gap-1">{(["yes", "no", "na"] as Answer[]).map((answer) => <button type="button" key={answer} aria-pressed={answers[key] === answer} onClick={() => setAnswers((current) => ({ ...current, [key]: answer }))} className={`min-h-10 min-w-11 rounded-md border px-2 text-xs font-semibold uppercase ${answers[key] === answer ? "border-brand-gold bg-brand-gold text-brand-black" : "border-iron-200"}`}>{answer === "na" ? "N/A" : answer}</button>)}</div></div>)}</div></section>

      <section><div className="flex flex-wrap items-center justify-between gap-2"><div><h3 className="font-semibold text-iron-900">3. Tasks, hazards and controls</h3><p className="text-xs text-iron-500">Use a preset or add custom work. Critical rows require an accepted control, owner and required evidence.</p></div><div className="flex flex-wrap gap-2">{Object.keys(presets).map((key) => <button key={key} type="button" onClick={() => addPreset(key)} className="rounded-md border border-brand-gold px-3 py-2 text-xs font-semibold capitalize">+ {key} preset</button>)}</div></div><div className="mt-2 flex flex-wrap gap-2"><button type="button" onClick={saveProjectPreset} className="rounded-md border px-3 py-2 text-xs font-semibold">Save rows as project preset</button>{(projectPresets[projectId] ?? []).map((_preset, index) => <button type="button" key={index} onClick={() => addProjectPreset(index)} className="rounded-md border px-3 py-2 text-xs font-semibold">Use project preset {index + 1}</button>)}</div>
        <div className="mt-3 space-y-3">{rows.map((row, index) => <article key={row.id} className="rounded-lg border border-iron-100 p-3"><div className="mb-2 flex justify-between"><b className="text-sm">Task {index + 1}</b><button type="button" aria-label={`Remove task ${index + 1}`} onClick={() => setRows((current) => current.filter((item) => item.id !== row.id))}><Trash2 className="h-4 w-4 text-iron-500" /></button></div><div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4"><Field label="Task" value={row.task} onChange={(value) => updateRow(row.id, { task: value })} required /><Field label="Hazard" value={row.hazard} onChange={(value) => updateRow(row.id, { hazard: value })} required /><Field label="Control" value={row.control} onChange={(value) => updateRow(row.id, { control: value })} required /><Field label="Responsible person" value={row.responsible_person} onChange={(value) => updateRow(row.id, { responsible_person: value })} required /><label className="grid gap-1 text-sm font-medium"><span>Control hierarchy</span><select value={row.control_type} onChange={(event) => updateRow(row.id, { control_type: event.target.value })} className="min-h-11 rounded-md border border-iron-200 px-3">{hierarchy.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><Field label="Evidence / photo reference" value={row.evidence} onChange={(value) => updateRow(row.id, { evidence: value })} /><div className="flex flex-wrap items-center gap-4 text-sm"><label><input type="checkbox" checked={row.critical} onChange={(event) => updateRow(row.id, { critical: event.target.checked })} /> Critical</label><label><input type="checkbox" checked={row.control_accepted} onChange={(event) => updateRow(row.id, { control_accepted: event.target.checked })} /> Control accepted</label><label><input type="checkbox" checked={row.evidence_required} onChange={(event) => updateRow(row.id, { evidence_required: event.target.checked })} /> Evidence required</label></div></div></article>)}</div><button type="button" onClick={() => setRows((current) => [...current, blankRow()])} className="mt-3 inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-semibold"><Plus className="h-4 w-4" />Add custom row</button></section>

      <section><h3 className="font-semibold text-iron-900">4. Emergency response and evidence</h3><div className="mt-3 grid gap-3 sm:grid-cols-2"><Field label="Muster point" value={muster} onChange={setMuster} required /><Field label="First aid response" value={firstAidPlan} onChange={setFirstAidPlan} required /><Field label="Communication" value={communication} onChange={setCommunication} required /><Field label="Stop-work triggers" value={stopWork} onChange={setStopWork} required /></div><div className="mt-3"><UniversalPhotoField files={files} onFilesChange={setFiles} label="FLHA photos / attachments" /></div></section>
      <div className="rounded-md bg-amber-50 p-3 text-xs leading-5 text-amber-900"><b>Release gate:</b> Missing fields, incomplete screening, uncontrolled critical hazards, missing evidence or unsigned crew keep this FLHA blocked. Re-assess after material scope, weather, crew, equipment or condition changes.</div>
      <button disabled={saving || !projectId || !site || !crew.length} className="min-h-12 w-full rounded-md bg-brand-gold px-4 py-3 text-sm font-semibold text-brand-black disabled:opacity-50">{saving ? "Saving FLHA…" : editingId ? "Update unsigned FLHA" : "Save draft for crew review"}</button>
    </form>
    <FlhaRegister records={flhas} employees={data.employees} onEdit={editRecord} onSaved={onSaved} onError={onError} />
  </div>;
}

function FlhaRegister({ records, employees, onEdit, onSaved, onError }: { records: FieldRecord[]; employees: FieldOperationsBootstrap["employees"]; onEdit: (record: FieldRecord) => void; onSaved: () => Promise<void>; onError: (value: string | null) => void }) {
  const [signer, setSigner] = useState<Record<string, string>>({});
  async function run(action: () => Promise<unknown>) { try { onError(null); await action(); await onSaved(); } catch (current) { onError(current instanceof Error ? current.message : "Unable to update FLHA."); } }
  return <section className="rounded-xl border border-iron-100 bg-white p-4 shadow-sm sm:p-6"><h2 className="font-semibold text-iron-950">FLHA records and acknowledgements</h2><div className="mt-3 space-y-3">{records.slice(0, 8).map((record) => { const blockers = (record.details.blockers as string[] | undefined) ?? []; return <article key={record.id} className="break-inside-avoid rounded-lg border border-iron-100 p-4"><div className="flex flex-wrap justify-between gap-2"><div><b>{record.title}</b><div className="text-xs text-iron-500">Version {String(record.details.version ?? 1)} · {record.work_date} · {record.signatures.length} signature(s) · {record.document_ids.length} attachment(s)</div></div><span className={`rounded-full px-3 py-1 text-xs font-semibold ${record.status === "released" ? "bg-emerald-100 text-emerald-800" : record.status === "blocked" ? "bg-red-100 text-red-800" : "bg-amber-100 text-amber-800"}`}>{record.status}</span></div>{blockers.length ? <div className="mt-2 flex gap-2 rounded-md bg-red-50 p-2 text-xs text-red-800"><AlertTriangle className="h-4 w-4 shrink-0" /><span>{blockers.join(" · ")}</span></div> : null}{record.document_ids.length ? <div className="mt-3"><UniversalPhotoField documentIds={record.document_ids} /></div> : null}<div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">{record.signatures.length === 0 && record.status !== "released" ? <button type="button" onClick={() => onEdit(record)} className="rounded-md border px-3 py-2 text-xs font-semibold">Edit unsigned draft</button> : null}<select value={signer[record.id] ?? ""} onChange={(event) => setSigner((current) => ({ ...current, [record.id]: event.target.value }))} disabled={record.status !== "draft"} className="min-h-10 rounded-md border px-2 text-sm"><option value="">Worker signing</option>{employees.map((employee) => <option key={employee.id} value={employee.id}>{employee.first_name} {employee.last_name}</option>)}</select><button type="button" disabled={!signer[record.id] || record.status !== "draft"} onClick={() => { const employee = employees.find((item) => item.id === signer[record.id]); if (employee) void run(() => fieldOperationsApi.signRecord(record.id, { employee_id: employee.id, employee_name: `${employee.first_name} ${employee.last_name}`, acknowledgement: "I reviewed this FLHA, understand the controls, and will stop work when conditions change.", signing_mode: "supervised_shared_device" })); }} className="rounded-md border border-brand-gold px-3 py-2 text-xs font-semibold disabled:opacity-40">Supervised sign</button><button type="button" disabled={record.status === "released"} onClick={() => { const reason = window.prompt("What materially changed?"); if (reason) void run(() => fieldOperationsApi.reassessRecord(record.id, { change_reason: reason, changed_conditions: ["conditions"] })); }} className="inline-flex items-center justify-center gap-1 rounded-md border px-3 py-2 text-xs font-semibold disabled:opacity-40"><RotateCcw className="h-3 w-3" />Re-assess</button><a href={fieldOperationsApi.pdfUrl(record.id)} target="_blank" rel="noreferrer" className="inline-flex items-center justify-center gap-1 rounded-md border px-3 py-2 text-xs font-semibold"><FileDown className="h-3 w-3" />PDF</a></div>{record.status === "draft" ? <button type="button" onClick={() => void run(() => fieldOperationsApi.releaseRecord(record.id, { field_conditions_verified: true, supervisor_name: String(record.details.supervisor ?? "Foreperson"), acknowledgement: "I verified actual field conditions, controls, evidence and crew acknowledgement at this work location." }))} className="mt-2 inline-flex items-center gap-2 rounded-md bg-iron-950 px-3 py-2 text-xs font-semibold text-white"><ShieldCheck className="h-4 w-4" />Verify conditions and release</button> : record.status === "released" ? <div className="mt-2 flex items-center gap-2 text-xs font-semibold text-emerald-700"><CheckCircle2 className="h-4 w-4" />Signed version frozen; changes require a new version.</div> : null}<details className="mt-2 text-xs text-iron-500"><summary>Audit history ({Array.isArray(record.details.audit) ? record.details.audit.length : 0})</summary><ol className="mt-1 space-y-1">{(record.details.audit as Array<Record<string, string>> | undefined)?.map((event, index) => <li key={`${event.at}-${index}`}>{event.at} · {event.action} · {event.actor_name}</li>)}</ol></details></article>; })}{!records.length ? <p className="rounded-md bg-iron-50 p-4 text-sm text-iron-500">No FLHA records yet.</p> : null}</div></section>;
}
