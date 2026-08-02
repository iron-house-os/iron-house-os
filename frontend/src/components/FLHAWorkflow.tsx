import { AlertOctagon, CheckCircle2, Download, History, Plus, RefreshCw, ShieldCheck, Trash2, Users } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { Employee, FieldOperationsBootstrap, FieldRecord, fieldOperationsApi } from "../api/fieldOperations";
import { mediaApi } from "../api/media";
import { useAuth } from "../contexts/AuthContext";
import { UniversalPhotoField } from "./UniversalPhotoField";

const SCREENING = [
  ["first_aid_equipment", "First aid equipment"],
  ["overhead_hazards", "Overhead hazards"],
  ["underground_utilities_and_locates", "Underground utilities and current locates"],
  ["mobile_equipment", "Mobile equipment"],
  ["confined_space", "Confined space"],
  ["excavation_sloping_shoring_and_access", "Excavation sloping / shoring and safe access"],
  ["additional_ppe", "Additional PPE"],
  ["traffic_control", "Traffic control"],
  ["subcontractors", "Subcontractors"],
  ["basic_ppe_review", "Basic PPE review"],
] as const;

type Answer = "yes" | "no" | "na";
type HazardRow = {
  task: string;
  hazard: string;
  control: string;
  responsible_person: string;
  control_level: "elimination" | "substitution" | "engineering" | "administrative" | "ppe";
  risk: "low" | "medium" | "high" | "critical";
  accepted_control: boolean;
  evidence_required: boolean;
  evidence: string;
};

const emptyHazard = (): HazardRow => ({
  task: "", hazard: "", control: "", responsible_person: "", control_level: "administrative",
  risk: "medium", accepted_control: false, evidence_required: false, evidence: "",
});
const localDateTime = () => {
  const current = new Date();
  return new Date(current.getTime() - current.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
};
const employeeName = (employee: Employee) => `${employee.first_name} ${employee.last_name}`;

type Props = {
  data: FieldOperationsBootstrap;
  canCreate: boolean;
  onSaved: () => Promise<void>;
  onError: (message: string | null) => void;
};

export function FLHAWorkflow({ data, canCreate, onSaved, onError }: Props) {
  const { user } = useAuth();
  const currentEmployee = data.employees.find((item) => item.email.toLowerCase() === user?.email.toLowerCase());
  const records = data.records.filter((item) => item.record_type === "daily_hazard_assessment");
  const [editing, setEditing] = useState<FieldRecord | null>(null);
  const [reassessment, setReassessment] = useState<{ sourceId: string; reason: string } | null>(null);
  const [changedConditions, setChangedConditions] = useState<string[]>(["conditions"]);
  const [projectId, setProjectId] = useState(data.projects[0]?.id ?? "");
  const [site, setSite] = useState("");
  const [assessmentDateTime, setAssessmentDateTime] = useState(localDateTime());
  const [supervisorId, setSupervisorId] = useState(currentEmployee?.id ?? "");
  const [firstAidId, setFirstAidId] = useState(data.employees.find((item) => /first aid/i.test(item.role ?? ""))?.id ?? "");
  const [crewIds, setCrewIds] = useState<string[]>([]);
  const [weather, setWeather] = useState("");
  const [screening, setScreening] = useState<Record<string, Answer>>({});
  const [hazards, setHazards] = useState<HazardRow[]>([emptyHazard()]);
  const [emergency, setEmergency] = useState({ response_plan: "Call 911, provide site access details and notify the supervisor", muster_point: "", first_aid_location: "", communication: "Mobile phone / two-way radio", stop_work_triggers: "Conditions change, control fails, worker is unsure, or a new critical hazard is identified" });
  const [files, setFiles] = useState<File[]>([]);
  const [saving, setSaving] = useState(false);
  const [sharedSigner, setSharedSigner] = useState<Record<string, string>>({});

  const selectedProject = data.projects.find((item) => item.id === projectId);
  const latestWeather = useMemo(() => data.records.find((item) => item.record_type === "weather" && (!projectId || item.project_id === projectId)), [data.records, projectId]);
  useEffect(() => {
    if (!weather && latestWeather) setWeather(String(latestWeather.details.weather ?? latestWeather.details.notes ?? ""));
  }, [latestWeather, weather]);
  useEffect(() => {
    if (editing || crewIds.length || !projectId) return;
    const scheduled = data.records.filter((item) => item.record_type === "crew_shift" && item.project_id === projectId && item.work_date === assessmentDateTime.slice(0, 10)).map((item) => item.employee_id).filter((value): value is string => Boolean(value));
    if (scheduled.length) setCrewIds([...new Set(scheduled)]);
  }, [assessmentDateTime, crewIds.length, data.records, editing, projectId]);

  function details() {
    const supervisor = data.employees.find((item) => item.id === supervisorId);
    const firstAid = data.employees.find((item) => item.id === firstAidId);
    return {
      project_name: selectedProject?.name ?? "",
      site_location: site,
      assessment_datetime: assessmentDateTime,
      supervisor: { id: supervisor?.id ?? "", name: supervisor ? employeeName(supervisor) : "" },
      first_aid_attendant: { id: firstAid?.id ?? "", name: firstAid ? employeeName(firstAid) : "" },
      crew: crewIds.map((id) => data.employees.find((item) => item.id === id)).filter((item): item is Employee => Boolean(item)).map((item) => ({ id: item.id, name: employeeName(item) })),
      weather,
      screening,
      hazards,
      emergency,
      field_verification_required: true,
      ai_suggestions_are_unverified: true,
    };
  }

  function reset() {
    setEditing(null); setReassessment(null); setChangedConditions(["conditions"]); setSite(""); setAssessmentDateTime(localDateTime()); setCrewIds([]); setWeather("");
    setScreening({}); setHazards([emptyHazard()]); setFiles([]);
    setEmergency({ response_plan: "Call 911, provide site access details and notify the supervisor", muster_point: "", first_aid_location: "", communication: "Mobile phone / two-way radio", stop_work_triggers: "Conditions change, control fails, worker is unsure, or a new critical hazard is identified" });
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); onError(null);
    try {
      const uploaded = files.length ? await mediaApi.upload({ files, projectId: projectId || undefined, caption: "FLHA field evidence", capturedDate: assessmentDateTime.slice(0, 10), category: "flha" }) : [];
      const documentIds = [...(editing?.document_ids ?? []), ...uploaded.map((asset) => asset.original_document_id)];
      const payload = { project_id: projectId || null, work_date: assessmentDateTime.slice(0, 10), title: `${selectedProject?.name ?? "Field work"} FLHA`, details: details(), document_ids: documentIds };
      let saved: FieldRecord;
      if (reassessment) saved = await fieldOperationsApi.reassessFlha(reassessment.sourceId, { ...payload, reason: reassessment.reason, changed_conditions: changedConditions });
      else if (editing) saved = await fieldOperationsApi.updateFlha(editing.id, payload);
      else saved = await fieldOperationsApi.createRecord({ record_type: "daily_hazard_assessment", ...payload });
      await Promise.all(uploaded.map((asset) => mediaApi.link(asset.id, "field_record", saved.id)));
      reset(); await onSaved();
    } catch (failure) { onError(failure instanceof Error ? failure.message : "Unable to save the FLHA."); }
    finally { setSaving(false); }
  }

  function loadRecord(record: FieldRecord, asReassessment = false) {
    const value = record.details;
    setEditing(asReassessment ? null : record);
    setReassessment(asReassessment ? { sourceId: record.id, reason: window.prompt("Why is this re-assessment required?") ?? "Material field conditions changed" } : null);
    setProjectId(record.project_id ?? ""); setSite(String(value.site_location ?? "")); setAssessmentDateTime(localDateTime());
    setSupervisorId(String((value.supervisor as Record<string, unknown> | undefined)?.id ?? ""));
    setFirstAidId(String((value.first_aid_attendant as Record<string, unknown> | undefined)?.id ?? ""));
    setCrewIds(((value.crew as Array<Record<string, string>> | undefined) ?? []).map((item) => item.id));
    setWeather(String(value.weather ?? "")); setScreening((value.screening as Record<string, Answer>) ?? {});
    setHazards(((value.hazards as HazardRow[] | undefined) ?? [emptyHazard()]).map((item) => ({ ...item })));
    setEmergency({ ...emergency, ...((value.emergency as typeof emergency | undefined) ?? {}) }); setFiles([]);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function addPreset(index: number) {
    const preset = data.flha_presets.filter((item) => item.scope === "company" || item.project_id === projectId)[index];
    if (!preset) return;
    const rows = preset.rows.map((row) => ({ ...emptyHazard(), ...row })) as HazardRow[];
    setHazards((current) => [...current.filter((item) => item.task || item.hazard || item.control), ...rows]);
  }

  const localCriticalBlockers = hazards.filter((row) => row.risk === "critical" && (!row.accepted_control || !row.responsible_person || (row.evidence_required && !row.evidence))).length;

  return <div className="space-y-5">
    {canCreate ? <form onSubmit={submit} className="rounded-xl border border-brand-gold/40 bg-white p-4 shadow-sm sm:p-5">
      <div className="flex items-start gap-3"><ShieldCheck className="mt-0.5 h-6 w-6 shrink-0 text-brand-gold-dark" /><div><h2 className="font-semibold text-iron-950">{reassessment ? "FLHA re-assessment" : editing ? "Edit FLHA draft" : "Daily FLHA"}</h2><p className="mt-1 text-sm text-iron-500">Fast field screening, task controls, crew acknowledgement and supervisor release.</p></div></div>
      {reassessment ? <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"><div>New immutable version · Reason: {reassessment.reason}</div><fieldset className="mt-2"><legend className="font-semibold">Material changes</legend><div className="mt-1 flex flex-wrap gap-3">{["scope", "weather", "crew", "equipment", "conditions"].map((trigger) => <label key={trigger} className="flex min-h-11 items-center gap-2 capitalize"><input type="checkbox" checked={changedConditions.includes(trigger)} onChange={(event) => setChangedConditions(event.target.checked ? [...changedConditions, trigger] : changedConditions.filter((item) => item !== trigger))} />{trigger}</label>)}</div></fieldset></div> : null}
      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <SelectField label="Project / job" value={projectId} onChange={setProjectId} options={data.projects.map((item) => [item.id, item.name])} />
        <TextField label="Site / location" value={site} onChange={setSite} />
        <TextField label="Date and time" value={assessmentDateTime} onChange={setAssessmentDateTime} type="datetime-local" />
        <SelectField label="Supervisor / foreperson" value={supervisorId} onChange={setSupervisorId} options={data.employees.map((item) => [item.id, employeeName(item)])} />
        <SelectField label="First aid attendant" value={firstAidId} onChange={setFirstAidId} options={data.employees.map((item) => [item.id, employeeName(item)])} />
        <TextField label="Weather / temperature" value={weather} onChange={setWeather} />
      </div>
      <fieldset className="mt-5 rounded-lg bg-iron-50 p-4"><legend className="px-1 text-sm font-semibold text-iron-800">Crew required to review and sign</legend><div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{data.employees.map((employee) => <label key={employee.id} className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={crewIds.includes(employee.id)} onChange={(event) => setCrewIds(event.target.checked ? [...crewIds, employee.id] : crewIds.filter((id) => id !== employee.id))} />{employeeName(employee)}</label>)}</div></fieldset>
      <fieldset className="mt-5"><legend className="font-semibold text-iron-950">Rapid hazard screening</legend><div className="mt-3 grid gap-2 lg:grid-cols-2">{SCREENING.map(([key, label]) => <div key={key} className="grid grid-cols-[1fr_auto] items-center gap-2 rounded-md border border-iron-100 p-2"><span className="text-sm text-iron-700">{label}</span><div className="flex gap-1">{(["yes", "no", "na"] as Answer[]).map((answer) => <button key={answer} type="button" aria-pressed={screening[key] === answer} onClick={() => setScreening((current) => ({ ...current, [key]: answer }))} className={`min-h-11 min-w-11 rounded px-2 text-xs font-semibold uppercase ${screening[key] === answer ? "bg-brand-gold text-brand-black" : "border border-iron-100 bg-white text-iron-600"}`}>{answer === "na" ? "N/A" : answer}</button>)}</div></div>)}</div></fieldset>
      <section className="mt-5"><div className="flex flex-wrap items-center justify-between gap-2"><div><h3 className="font-semibold text-iron-950">Tasks, hazards and controls</h3><p className="text-xs text-iron-500">Controls follow elimination, substitution, engineering, administrative and PPE.</p></div><div className="flex flex-wrap gap-2">{data.flha_presets.filter((preset) => preset.scope === "company" || preset.project_id === projectId).map((preset, index) => <button key={preset.id} type="button" onClick={() => addPreset(index)} className="min-h-11 rounded-md border border-brand-gold px-3 text-xs font-semibold">Add {preset.name}</button>)}<button type="button" onClick={() => setHazards((current) => [...current, emptyHazard()])} className="flex min-h-11 items-center gap-1 rounded-md bg-brand-gold px-3 text-sm font-semibold text-brand-black"><Plus className="h-4 w-4" />Custom row</button></div></div>
        <div className="mt-3 space-y-3">{hazards.map((row, index) => <HazardEditor key={index} row={row} index={index} onChange={(next) => setHazards((current) => current.map((item, itemIndex) => itemIndex === index ? next : item))} onRemove={() => setHazards((current) => current.filter((_, itemIndex) => itemIndex !== index))} />)}</div>
      </section>
      <section className="mt-5"><h3 className="font-semibold text-iron-950">Emergency response and stop-work</h3><div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{Object.entries(emergency).map(([key, value]) => <TextField key={key} label={key.replaceAll("_", " ")} value={value} onChange={(next) => setEmergency((current) => ({ ...current, [key]: next }))} />)}</div></section>
      <div className="mt-5"><UniversalPhotoField files={files} onFilesChange={setFiles} category="flha" label="FLHA photos / control evidence" /></div>
      <div className={`mt-5 rounded-md p-3 text-sm ${localCriticalBlockers ? "bg-red-50 text-red-800" : "bg-emerald-50 text-emerald-800"}`}>{localCriticalBlockers ? <><AlertOctagon className="mr-2 inline h-4 w-4" />Blocked: {localCriticalBlockers} critical hazard(s) still need an accepted control, responsible person or evidence.</> : <><CheckCircle2 className="mr-2 inline h-4 w-4" />No locally detected uncontrolled critical hazards. The responsible field person must still verify actual conditions.</>}</div>
      <div className="mt-4 flex flex-wrap gap-2"><button type="submit" disabled={saving} className="min-h-11 rounded-md bg-brand-gold px-4 text-sm font-semibold text-brand-black disabled:opacity-50">{saving ? "Saving…" : reassessment ? "Create re-assessment" : editing ? "Save draft changes" : "Save FLHA draft"}</button>{editing || reassessment ? <button type="button" onClick={reset} className="min-h-11 rounded-md border border-iron-100 px-4 text-sm font-semibold">Cancel</button> : null}</div>
      <p className="mt-3 text-xs leading-5 text-iron-500">AI suggestions, if used, are planning aids only and never mark an FLHA safe or complete.</p>
    </form> : null}
    <section className="rounded-xl border border-iron-100 bg-white p-4 shadow-sm sm:p-5"><div className="flex items-start gap-3"><History className="mt-0.5 h-5 w-5 text-brand-gold-dark" /><div><h2 className="font-semibold text-iron-950">FLHA records and acknowledgements</h2><p className="mt-1 text-sm text-iron-500">Signed versions are frozen. Material changes require a new version and fresh crew acknowledgement.</p></div></div><div className="mt-4 space-y-3">{records.map((record) => <FLHARecordCard key={record.id} record={record} employees={data.employees} currentEmployee={currentEmployee} canCreate={canCreate} sharedSigner={sharedSigner[record.id] ?? ""} setSharedSigner={(value) => setSharedSigner((current) => ({ ...current, [record.id]: value }))} onEdit={() => loadRecord(record)} onReassess={() => loadRecord(record, true)} onSaved={onSaved} onError={onError} />)}{!records.length ? <div className="rounded-md bg-iron-50 p-4 text-sm text-iron-500">No FLHA records yet.</div> : null}</div></section>
  </div>;
}

function FLHARecordCard({ record, employees, currentEmployee, canCreate, sharedSigner, setSharedSigner, onEdit, onReassess, onSaved, onError }: { record: FieldRecord; employees: Employee[]; currentEmployee?: Employee; canCreate: boolean; sharedSigner: string; setSharedSigner: (value: string) => void; onEdit: () => void; onReassess: () => void; onSaved: () => Promise<void>; onError: (value: string | null) => void }) {
  const crew = (record.details.crew as Array<Record<string, string>> | undefined) ?? [];
  const audit = (record.details.audit_history as Array<Record<string, string>> | undefined) ?? [];
  const blockers = (record.details.release_blockers as string[] | undefined) ?? [];
  const signedIds = new Set(record.signatures.map((item) => item.employee_id));
  const mySignaturePending = currentEmployee && crew.some((item) => item.id === currentEmployee.id) && !signedIds.has(currentEmployee.id);
  const pendingCrew = crew.filter((item) => !signedIds.has(item.id));
  async function sign(employee: Employee, supervised = false) {
    try { await fieldOperationsApi.signRecord(record.id, { employee_id: employee.id, employee_name: employeeName(employee), acknowledgement: "I reviewed this FLHA, understand the hazards and controls, and will stop work if conditions change.", supervised_shared_device: supervised, supervisor_confirmation: supervised ? "I supervised this worker reviewing and applying their own acknowledgement on the shared device." : null }); await onSaved(); }
    catch (failure) { onError(failure instanceof Error ? failure.message : "Unable to acknowledge the FLHA."); }
  }
  async function release() {
    const verification = window.prompt("Confirm how you verified actual field conditions and crew acknowledgement:");
    if (!verification) return;
    try { await fieldOperationsApi.releaseFlha(record.id, verification); await onSaved(); }
    catch (failure) { onError(failure instanceof Error ? failure.message : "Unable to release the FLHA."); }
  }
  return <article className="rounded-lg border border-iron-100 p-4"><div className="flex flex-wrap items-start justify-between gap-2"><div><h3 className="font-semibold text-iron-950">{record.title}</h3><div className="mt-1 text-xs uppercase tracking-wide text-iron-500">Version {String(record.details.version ?? 1)} · {record.work_date} · {record.status}</div></div><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${record.status === "blocked" ? "bg-red-100 text-red-800" : record.status === "released" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>{record.status}</span></div>
    <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2"><div>{String(record.details.site_location ?? "Location not entered")}</div><div>{String(record.details.weather ?? "Weather not entered")}</div><div><Users className="mr-1 inline h-4 w-4" />{record.signatures.length}/{crew.length} acknowledged</div><div>{record.document_ids.length} attachment(s)</div></div>
    {blockers.length && record.status !== "released" ? <div className="mt-3 rounded-md bg-amber-50 p-3 text-xs text-amber-900">Release checks: {blockers.slice(0, 3).join(" ")}{blockers.length > 3 ? ` +${blockers.length - 3} more` : ""}</div> : null}
    <div className="mt-3 flex flex-wrap gap-2"><a href={fieldOperationsApi.flhaPdfUrl(record.id)} className="flex min-h-11 items-center gap-1 rounded-md border border-iron-100 px-3 text-sm font-semibold"><Download className="h-4 w-4" />PDF</a>{canCreate && !record.signatures.length && record.status !== "released" ? <button type="button" onClick={onEdit} className="min-h-11 rounded-md border border-brand-gold px-3 text-sm font-semibold">Edit draft</button> : null}{canCreate && (record.signatures.length > 0 || record.status === "released") ? <button type="button" onClick={onReassess} className="flex min-h-11 items-center gap-1 rounded-md border border-brand-gold px-3 text-sm font-semibold"><RefreshCw className="h-4 w-4" />Re-assess</button> : null}{mySignaturePending ? <button type="button" onClick={() => void sign(currentEmployee)} className="min-h-11 rounded-md bg-brand-gold px-3 text-sm font-semibold text-brand-black">Review and sign on my device</button> : null}{canCreate && record.status !== "released" ? <button type="button" onClick={() => void release()} className="min-h-11 rounded-md bg-iron-950 px-3 text-sm font-semibold text-white">Supervisor release</button> : null}</div>
    {canCreate && pendingCrew.length ? <div className="mt-3 grid gap-2 rounded-md bg-iron-50 p-3 sm:grid-cols-[1fr_auto]"><select aria-label="Worker using supervised shared device" value={sharedSigner} onChange={(event) => setSharedSigner(event.target.value)} className="min-h-11 rounded-md border border-iron-100 bg-white px-3 text-sm"><option value="">Supervised shared-device worker…</option>{pendingCrew.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}</select><button type="button" disabled={!sharedSigner} onClick={() => { const employee = employees.find((item) => item.id === sharedSigner); if (employee) void sign(employee, true); }} className="min-h-11 rounded-md border border-brand-gold px-3 text-sm font-semibold disabled:opacity-50">Supervise acknowledgement</button></div> : null}
    {record.document_ids.length ? <div className="mt-3"><UniversalPhotoField documentIds={record.document_ids} category="flha" /></div> : null}
    <details className="mt-3"><summary className="cursor-pointer text-sm font-semibold text-iron-700">Audit history ({audit.length} events)</summary><ol className="mt-2 space-y-1 text-xs text-iron-500">{audit.map((event, index) => <li key={index}>{event.at} · {String(event.action).replaceAll("_", " ")} · {event.display_name ?? event.by}</li>)}</ol></details>
  </article>;
}

function HazardEditor({ row, index, onChange, onRemove }: { row: HazardRow; index: number; onChange: (row: HazardRow) => void; onRemove: () => void }) {
  return <div className={`rounded-lg border p-3 ${row.risk === "critical" && (!row.accepted_control || !row.responsible_person || (row.evidence_required && !row.evidence)) ? "border-red-300 bg-red-50/40" : "border-iron-100"}`}><div className="flex items-center justify-between"><span className="text-xs font-semibold uppercase tracking-wide text-brand-gold-dark">Task row {index + 1}</span><button type="button" aria-label={`Remove task row ${index + 1}`} onClick={onRemove} className="min-h-11 min-w-11 rounded-md text-red-700"><Trash2 className="mx-auto h-4 w-4" /></button></div><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><TextField label="Task" value={row.task} onChange={(value) => onChange({ ...row, task: value })} /><TextField label="Hazard" value={row.hazard} onChange={(value) => onChange({ ...row, hazard: value })} /><TextField label="Control" value={row.control} onChange={(value) => onChange({ ...row, control: value })} /><TextField label="Responsible person" value={row.responsible_person} onChange={(value) => onChange({ ...row, responsible_person: value })} /><SelectField label="Control hierarchy" value={row.control_level} onChange={(value) => onChange({ ...row, control_level: value as HazardRow["control_level"] })} options={[["elimination", "Elimination"], ["substitution", "Substitution"], ["engineering", "Engineering"], ["administrative", "Administrative"], ["ppe", "PPE"]]} /><SelectField label="Risk" value={row.risk} onChange={(value) => onChange({ ...row, risk: value as HazardRow["risk"] })} options={[["low", "Low"], ["medium", "Medium"], ["high", "High"], ["critical", "Critical"]]} /><label className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={row.accepted_control} onChange={(event) => onChange({ ...row, accepted_control: event.target.checked })} />Control accepted after field verification</label><label className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={row.evidence_required} onChange={(event) => onChange({ ...row, evidence_required: event.target.checked })} />Evidence required</label>{row.evidence_required ? <TextField label="Required evidence / reference" value={row.evidence} onChange={(value) => onChange({ ...row, evidence: value })} /> : null}</div></div>;
}

function TextField({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (value: string) => void; type?: string }) { return <label className="grid gap-1 text-sm"><span className="capitalize font-medium text-iron-700">{label}</span><input type={type} value={value} onChange={(event) => onChange(event.target.value)} className="min-h-11 rounded-md border border-iron-100 px-3" /></label>; }
function SelectField({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: string[][] }) { return <label className="grid gap-1 text-sm"><span className="font-medium text-iron-700">{label}</span><select value={value} onChange={(event) => onChange(event.target.value)} className="min-h-11 rounded-md border border-iron-100 bg-white px-3"><option value="">Select…</option>{options.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>; }
