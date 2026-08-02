import { AlertTriangle, CheckCircle2, ClipboardCheck, Download, Plus, RefreshCw, ShieldCheck, Sparkles, Trash2 } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  Employee,
  FieldOperationsBootstrap,
  FieldRecord,
  FLHADetails,
  FLHATask,
  fieldOperationsApi,
} from "../api/fieldOperations";
import { MediaAsset } from "../api/media";
import { UniversalPhotoField } from "../components/UniversalPhotoField";
import { useAuth } from "../contexts/AuthContext";

const screening = [
  ["first_aid_equipment", "First aid equipment available"],
  ["overhead_hazards", "Overhead hazards"],
  ["underground_utilities_locates", "Underground utilities and current locates"],
  ["mobile_equipment", "Mobile equipment interaction"],
  ["confined_space", "Confined space"],
  ["excavation_sloping_shoring_access", "Excavation sloping, shoring and safe access"],
  ["additional_ppe", "Additional PPE"],
  ["traffic_control", "Traffic control"],
  ["subcontractors", "Subcontractors"],
  ["basic_ppe_review", "Basic PPE reviewed"],
] as const;

const emptyTask = (): FLHATask => ({
  id: crypto.randomUUID(),
  task: "",
  hazard: "",
  control: "",
  control_hierarchy: "administrative",
  responsible_person: "",
  critical: false,
  control_accepted: false,
  evidence_required: false,
  evidence_ids: [],
  ai_suggested: false,
});

function initialDetails(): FLHADetails {
  return {
    site_location: "",
    started_at: new Date().toISOString(),
    supervisor_name: "",
    first_aid_attendant: "",
    crew: [],
    weather: "",
    screening: screening.map(([key]) => ({ key, response: "" as "yes", notes: null })),
    tasks: [emptyTask()],
    emergency_response: "",
    muster_point: "",
    communication_method: "",
    stop_work_triggers: ["Conditions change", "A control is missing or ineffective"],
    preset_names: [],
  };
}

function asDetails(record: FieldRecord): FLHADetails {
  return record.details as unknown as FLHADetails;
}

function Field({ label, value, onChange, required = true, type = "text" }: {
  label: string; value: string; onChange: (value: string) => void; required?: boolean; type?: string;
}) {
  return (
    <label className="grid gap-1 text-sm font-medium text-iron-700">
      {label}
      <input
        required={required}
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="min-h-11 rounded-md border border-iron-200 px-3 py-2 text-base focus:border-brand-gold focus:outline-none focus:ring-2 focus:ring-brand-gold/30"
      />
    </label>
  );
}

export function FLHAPage() {
  const { user, portalRole } = useAuth();
  const [bootstrap, setBootstrap] = useState<FieldOperationsBootstrap | null>(null);
  const [details, setDetails] = useState<FLHADetails>(initialDetails);
  const [projectId, setProjectId] = useState("");
  const [workDate, setWorkDate] = useState(new Date().toISOString().slice(0, 10));
  const [current, setCurrent] = useState<FieldRecord | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const canSupervise = user?.role === "admin" || user?.role === "operations_manager" || portalRole === "foreman" || portalRole === "management";

  const refresh = useCallback(async () => {
    const data = await fieldOperationsApi.bootstrap();
    setBootstrap(data);
    setProjectId((value) => value || String(data.projects[0]?.id ?? ""));
    const own = data.employees.find((employee) => employee.email.toLowerCase() === user?.email.toLowerCase());
    if (own) {
      setDetails((value) => value.crew.length ? value : {
        ...value,
        crew: [{ employee_id: own.id, employee_name: own.first_name + " " + own.last_name }],
        supervisor_name: portalRole === "foreman" ? own.first_name + " " + own.last_name : value.supervisor_name,
      });
    }
  }, [portalRole, user?.email]);

  useEffect(() => {
    void refresh().catch((error) => setMessage(error instanceof Error ? error.message : "Unable to load FLHA data."));
  }, [refresh]);

  const records = useMemo(
    () => (bootstrap?.records ?? []).filter((record) => record.record_type === "daily_hazard_assessment"),
    [bootstrap],
  );

  function loadRecord(record: FieldRecord) {
    setCurrent(record);
    setProjectId(record.project_id ?? "");
    setWorkDate(record.work_date);
    setDetails(asDetails(record));
    setMessage(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function updateTask(index: number, values: Partial<FLHATask>) {
    setDetails((currentDetails) => ({
      ...currentDetails,
      tasks: currentDetails.tasks.map((task, taskIndex) => taskIndex === index ? { ...task, ...values } : task),
    }));
  }

  function toggleCrew(employee: Employee) {
    setDetails((value) => {
      const selected = value.crew.some((member) => member.employee_id === employee.id);
      return {
        ...value,
        crew: selected
          ? value.crew.filter((member) => member.employee_id !== employee.id)
          : [...value.crew, { employee_id: employee.id, employee_name: employee.first_name + " " + employee.last_name }],
      };
    });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setMessage(null);
    try {
      if (details.screening.some((item) => !item.response)) throw new Error("Answer every Yes / No / N/A screening item.");
      const payload = { project_id: projectId, work_date: workDate, title: "Daily FLHA", details };
      const saved = current
        ? await fieldOperationsApi.updateFlha(current.id, { details, change_summary: "Field draft updated" })
        : await fieldOperationsApi.createFlha(payload);
      setCurrent(saved);
      setDetails(asDetails(saved));
      setMessage(saved.status === "blocked" ? "Saved, but work remains blocked until every critical control is verified." : "FLHA draft saved.");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to save FLHA.");
    } finally { setBusy(false); }
  }

  async function suggest(index: number) {
    const task = details.tasks[index];
    if (!task.task.trim()) { setMessage("Enter the task before requesting a suggestion."); return; }
    setBusy(true);
    try {
      const [suggestion] = await fieldOperationsApi.suggestFlha(task.task);
      updateTask(index, {
        hazard: suggestion.hazard,
        control: suggestion.control,
        control_hierarchy: suggestion.control_hierarchy,
        ai_suggested: true,
        control_accepted: false,
      });
      setMessage("AI suggestion added as an unaccepted draft. The responsible field person must verify it.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load a suggestion.");
    } finally { setBusy(false); }
  }

  async function release() {
    if (!current) return;
    setBusy(true); setMessage(null);
    try {
      const released = await fieldOperationsApi.releaseFlha(current.id, {
        field_conditions_verified: true,
        release_note: "Actual conditions verified at the work location.",
      });
      setCurrent(released); setDetails(asDetails(released)); setMessage("Supervisor release recorded. Crew acknowledgements are now required.");
      await refresh();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Unable to release FLHA."); }
    finally { setBusy(false); }
  }

  async function sign(member: { employee_id: string; employee_name: string }) {
    if (!current || !user) return;
    const supervised = user.email.toLowerCase() !== bootstrap?.employees.find((item) => item.id === member.employee_id)?.email.toLowerCase();
    setBusy(true); setMessage(null);
    try {
      const signed = await fieldOperationsApi.signFlha(current.id, {
        employee_id: member.employee_id,
        employee_name: member.employee_name,
        acknowledgement: "I reviewed the hazards and controls and will stop work if conditions change.",
        supervised_shared_device: supervised,
      });
      setCurrent(signed); setDetails(asDetails(signed)); setMessage("Crew acknowledgement recorded on this immutable version.");
      await refresh();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Unable to sign FLHA."); }
    finally { setBusy(false); }
  }

  async function reassess() {
    if (!current) return;
    const reason = window.prompt("What materially changed (scope, weather, crew, equipment or conditions)?")?.trim();
    if (!reason) return;
    setBusy(true); setMessage(null);
    try {
      const version = await fieldOperationsApi.reassessFlha(current.id, { reason, details });
      setCurrent(version); setDetails(asDetails(version));
      setMessage("A new auditable FLHA version was created. The prior signed record was not changed.");
      await refresh();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Unable to create reassessment."); }
    finally { setBusy(false); }
  }

  const onAssetsChange = useCallback((assets: MediaAsset[]) => {
    if (!assets.length) return;
    const ids = assets.map((asset) => asset.id);
    setDetails((value) => ({
      ...value,
      tasks: value.tasks.map((task) => task.evidence_required ? { ...task, evidence_ids: ids } : task),
    }));
  }, []);

  const blockers = current ? asDetails(current).release_blockers ?? [] : [];
  const signedIds = new Set((current?.signatures ?? []).map((signature) => signature.employee_id));
  const mutable = !current || ["draft", "blocked"].includes(current.status);

  return (
    <div className="mx-auto grid max-w-6xl gap-5 pb-24">
      <header className="ihos-brand-surface rounded-xl border border-brand-gold/30 px-5 py-5 text-white shadow-brand">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-gold">Safety · Daily field record</div>
            <h1 className="mt-2 text-2xl font-semibold text-brand-silver sm:text-3xl">Field Level Hazard Assessment</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-100">Plan the work, verify actual conditions, and collect each crew acknowledgement. AI remains advisory.</p>
          </div>
          {current ? <Status status={current.status} version={asDetails(current).flha_version ?? 1} /> : null}
        </div>
      </header>

      {message ? <div role="status" className="rounded-lg border border-brand-gold/40 bg-brand-gold/10 p-3 text-sm font-medium text-iron-900">{message}</div> : null}
      {blockers.length ? (
        <section role="alert" className="rounded-lg border border-red-300 bg-red-50 p-4 text-red-900">
          <div className="flex items-center gap-2 font-semibold"><AlertTriangle className="h-5 w-5" /> Work blocked</div>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}</ul>
        </section>
      ) : null}

      <form onSubmit={submit} className="grid gap-5">
        <fieldset disabled={!mutable} className="contents">
        <section className="rounded-xl border border-iron-100 bg-white p-4 shadow-sm sm:p-6">
          <h2 className="font-semibold text-iron-950">1. Job and crew</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="grid gap-1 text-sm font-medium text-iron-700">Project / job
              <select required disabled={!mutable} value={projectId} onChange={(event) => setProjectId(event.target.value)} className="min-h-11 rounded-md border border-iron-200 px-3 text-base">
                <option value="">Select project</option>
                {bootstrap?.projects.map((project) => <option key={project.id} value={project.id}>{String(project.name)}</option>)}
              </select>
            </label>
            <Field label="Date" type="date" value={workDate} onChange={setWorkDate} />
            <Field label="Site / location" value={details.site_location} onChange={(site_location) => setDetails({ ...details, site_location })} />
            <Field label="Weather / conditions" value={details.weather} onChange={(weather) => setDetails({ ...details, weather })} />
            <Field label="Supervisor / foreperson" value={details.supervisor_name} onChange={(supervisor_name) => setDetails({ ...details, supervisor_name })} />
            <Field label="First aid attendant" value={details.first_aid_attendant} onChange={(first_aid_attendant) => setDetails({ ...details, first_aid_attendant })} />
          </div>
          <fieldset className="mt-4">
            <legend className="text-sm font-semibold text-iron-800">Crew on this FLHA</legend>
            <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {bootstrap?.employees.map((employee) => (
                <label key={employee.id} className="flex min-h-11 items-center gap-2 rounded-md border border-iron-100 px-3 text-sm">
                  <input type="checkbox" disabled={!mutable} checked={details.crew.some((member) => member.employee_id === employee.id)} onChange={() => toggleCrew(employee)} />
                  {employee.first_name} {employee.last_name}
                </label>
              ))}
            </div>
          </fieldset>
        </section>

        <section className="rounded-xl border border-iron-100 bg-white p-4 shadow-sm sm:p-6">
          <h2 className="font-semibold text-iron-950">2. Fast hazard screening</h2>
          <div className="mt-4 grid gap-3">
            {screening.map(([key, label]) => {
              const item = details.screening.find((entry) => entry.key === key)!;
              return (
                <fieldset key={key} className="grid gap-2 rounded-lg border border-iron-100 p-3 sm:grid-cols-[1fr_auto] sm:items-center">
                  <legend className="sr-only">{label}</legend>
                  <span className="text-sm font-medium">{label}</span>
                  <div className="grid grid-cols-3 gap-1">
                    {(["yes", "no", "na"] as const).map((response) => (
                      <button key={response} type="button" disabled={!mutable} aria-pressed={item.response === response} onClick={() => setDetails({
                        ...details,
                        screening: details.screening.map((entry) => entry.key === key ? { ...entry, response } : entry),
                      })} className={"min-h-11 rounded-md border px-3 text-xs font-semibold uppercase " + (item.response === response ? "border-brand-gold bg-brand-gold text-brand-black" : "border-iron-200 bg-white")}>{response === "na" ? "N/A" : response}</button>
                    ))}
                  </div>
                </fieldset>
              );
            })}
          </div>
        </section>

        <section className="rounded-xl border border-iron-100 bg-white p-4 shadow-sm sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div><h2 className="font-semibold text-iron-950">3. Tasks, hazards and controls</h2><p className="mt-1 text-xs text-iron-500">Use the hierarchy: eliminate, substitute, engineer, administer, then PPE.</p></div>
            <button type="button" disabled={!mutable} onClick={() => setDetails({ ...details, tasks: [...details.tasks, emptyTask()] })} className="flex min-h-11 items-center gap-2 rounded-md border border-brand-gold px-3 text-sm font-semibold"><Plus className="h-4 w-4" /> Add row</button>
          </div>
          <div className="mt-4 grid gap-4">
            {details.tasks.map((task, index) => (
              <article key={task.id} className="grid gap-3 rounded-lg border border-iron-100 bg-iron-50 p-3">
                <div className="flex items-center justify-between"><b className="text-sm">Task {index + 1}</b><button type="button" disabled={!mutable || details.tasks.length === 1} onClick={() => setDetails({ ...details, tasks: details.tasks.filter((_, taskIndex) => taskIndex !== index) })} aria-label={"Remove task " + (index + 1)} className="rounded p-2 text-red-700"><Trash2 className="h-4 w-4" /></button></div>
                <div className="grid gap-3 lg:grid-cols-2">
                  <Field label="Task" value={task.task} onChange={(value) => updateTask(index, { task: value })} />
                  <Field label="Hazard" value={task.hazard} onChange={(value) => updateTask(index, { hazard: value })} />
                  <label className="grid gap-1 text-sm font-medium text-iron-700 lg:col-span-2">Control
                    <textarea required value={task.control} onChange={(event) => updateTask(index, { control: event.target.value, control_accepted: false })} className="min-h-20 rounded-md border border-iron-200 px-3 py-2 text-base" />
                  </label>
                  <label className="grid gap-1 text-sm font-medium text-iron-700">Control hierarchy
                    <select value={task.control_hierarchy} onChange={(event) => updateTask(index, { control_hierarchy: event.target.value as FLHATask["control_hierarchy"] })} className="min-h-11 rounded-md border border-iron-200 px-3">
                      {["elimination", "substitution", "engineering", "administrative", "ppe"].map((level) => <option key={level}>{level}</option>)}
                    </select>
                  </label>
                  <Field label="Responsible person" value={task.responsible_person} onChange={(value) => updateTask(index, { responsible_person: value })} />
                </div>
                <div className="flex flex-wrap gap-4 text-sm">
                  <label className="flex min-h-11 items-center gap-2"><input type="checkbox" checked={task.critical} onChange={(event) => updateTask(index, { critical: event.target.checked })} /> Critical hazard</label>
                  <label className="flex min-h-11 items-center gap-2"><input type="checkbox" checked={task.control_accepted} onChange={(event) => updateTask(index, { control_accepted: event.target.checked })} /> Field control accepted</label>
                  <label className="flex min-h-11 items-center gap-2"><input type="checkbox" checked={task.evidence_required} onChange={(event) => updateTask(index, { evidence_required: event.target.checked, evidence_ids: event.target.checked ? task.evidence_ids : [] })} /> Evidence required</label>
                </div>
                {task.ai_suggested ? <p className="rounded bg-amber-50 p-2 text-xs text-amber-900">AI draft — unaccepted until a responsible field person verifies it.</p> : null}
                <button type="button" disabled={!mutable || busy} onClick={() => void suggest(index)} className="flex min-h-11 items-center justify-center gap-2 rounded-md border border-iron-200 bg-white px-3 text-sm font-semibold"><Sparkles className="h-4 w-4 text-brand-gold-dark" /> Suggest hazard/control (advisory)</button>
              </article>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-iron-100 bg-white p-4 shadow-sm sm:p-6">
          <h2 className="font-semibold text-iron-950">4. Emergency and stop-work plan</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <Field label="Emergency response" value={details.emergency_response} onChange={(emergency_response) => setDetails({ ...details, emergency_response })} />
            <Field label="Muster point" value={details.muster_point} onChange={(muster_point) => setDetails({ ...details, muster_point })} />
            <Field label="Communication" value={details.communication_method} onChange={(communication_method) => setDetails({ ...details, communication_method })} />
            <Field label="Stop-work triggers (comma separated)" value={details.stop_work_triggers.join(", ")} onChange={(value) => setDetails({ ...details, stop_work_triggers: value.split(",").map((item) => item.trim()).filter(Boolean) })} />
          </div>
        </section>

        </fieldset>
        {current ? (
          <section className="rounded-xl border border-iron-100 bg-white p-4 shadow-sm sm:p-6">
            <h2 className="font-semibold text-iron-950">5. Required evidence and attachments</h2>
            <p className="mt-1 text-sm text-iron-500">Authorized photos stay in the shared IHOS viewer with immutable originals and version history.</p>
            <div className="mt-4"><UniversalPhotoField category="flha" projectId={projectId} recordType="field_record" recordId={current.id} label="FLHA photos / evidence" readOnly={!mutable} onAssetsChange={onAssetsChange} /></div>
          </section>
        ) : null}

        {mutable ? <button disabled={busy} className="min-h-12 rounded-md bg-brand-gold px-5 py-3 font-semibold text-brand-black shadow-sm disabled:opacity-50">{busy ? "Saving…" : current ? "Save FLHA changes" : "Create FLHA draft"}</button> : null}
      </form>

      {current ? (
        <section className="rounded-xl border border-brand-gold/30 bg-white p-4 shadow-sm sm:p-6">
          <h2 className="font-semibold text-iron-950">Release, acknowledgement and reassessment</h2>
          <p className="mt-2 text-sm text-iron-600">A supervisor release verifies actual field conditions. Each worker then acknowledges this exact version.</p>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {canSupervise && mutable ? <button type="button" disabled={busy} onClick={() => void release()} className="flex min-h-12 items-center justify-center gap-2 rounded-md bg-emerald-700 px-4 font-semibold text-white"><CheckCircle2 className="h-5 w-5" /> Verify field conditions and release</button> : null}
            <a href={fieldOperationsApi.flhaPdfUrl(current.id)} className="flex min-h-12 items-center justify-center gap-2 rounded-md border border-iron-200 px-4 font-semibold"><Download className="h-5 w-5" /> Export compact PDF</a>
            {["released", "signed"].includes(current.status) ? <button type="button" disabled={busy} onClick={() => void reassess()} className="flex min-h-12 items-center justify-center gap-2 rounded-md border border-brand-gold px-4 font-semibold"><RefreshCw className="h-5 w-5" /> Re-assess changed conditions</button> : null}
          </div>
          {["released", "signed"].includes(current.status) ? (
            <div className="mt-5 grid gap-2">
              {details.crew.map((member) => {
                const employee = bootstrap?.employees.find((item) => item.id === member.employee_id);
                const maySign = canSupervise || employee?.email.toLowerCase() === user?.email.toLowerCase();
                return <div key={member.employee_id} className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-iron-100 p-3"><span className="text-sm font-medium">{member.employee_name}</span>{signedIds.has(member.employee_id) ? <span className="text-sm font-semibold text-emerald-700">Signed</span> : maySign ? <button type="button" disabled={busy} onClick={() => void sign(member)} className="min-h-11 rounded-md bg-brand-gold px-4 text-sm font-semibold text-brand-black">Review and sign</button> : <span className="text-xs text-iron-500">Awaiting worker</span>}</div>;
              })}
            </div>
          ) : null}
        </section>
      ) : null}

      <section className="rounded-xl border border-iron-100 bg-white p-4 shadow-sm sm:p-6">
        <div className="flex items-center gap-2"><ClipboardCheck className="h-5 w-5 text-brand-gold-dark" /><h2 className="font-semibold">FLHA record history</h2></div>
        <div className="mt-3 grid gap-2">
          {records.length ? records.map((record) => <button type="button" key={record.id} onClick={() => loadRecord(record)} className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-iron-100 p-3 text-left"><span><b>{record.title}</b><span className="ml-2 text-xs text-iron-500">{record.work_date} · version {asDetails(record).flha_version ?? 1}</span></span><Status status={record.status} version={asDetails(record).flha_version ?? 1} compact /></button>) : <p className="rounded-md bg-iron-50 p-4 text-sm text-iron-500">No FLHA records available.</p>}
        </div>
      </section>
    </div>
  );
}

function Status({ status, version, compact = false }: { status: string; version: number; compact?: boolean }) {
  const style = status === "signed" ? "bg-emerald-100 text-emerald-900" : status === "blocked" ? "bg-red-100 text-red-900" : status === "released" ? "bg-blue-100 text-blue-900" : "bg-amber-100 text-amber-900";
  return <span className={"inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold uppercase " + style}>{compact ? null : <ShieldCheck className="h-4 w-4" />}V{version} · {status}</span>;
}

