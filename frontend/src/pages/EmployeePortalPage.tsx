import {
  AlertTriangle,
  BookOpenCheck,
  Camera,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  ExternalLink,
  FileText,
  Fuel,
  HardHat,
  RefreshCw,
  ShieldCheck,
  Truck,
  Users,
  Wrench,
} from "lucide-react";
import { FormEvent, ReactNode, useCallback, useEffect, useMemo, useState } from "react";

import { documentsApi } from "../api/documents";
import {
  Employee,
  FieldOperationsBootstrap,
  FieldRecord,
  fieldOperationsApi,
} from "../api/fieldOperations";

const SAFETY_PROGRAM_URL =
  "https://docs.google.com/document/d/1ApKQs4xIR8axW0lIaeqqATDVaZWs1jvSzaZwYK6wUNw/edit?usp=drivesdk";
const today = () => new Date().toISOString().slice(0, 10);
const money = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" });

function useFieldOperations() {
  const [data, setData] = useState<FieldOperationsBootstrap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await fieldOperationsApi.bootstrap());
    } catch (current) {
      setError(current instanceof Error ? current.message : "Unable to load field operations.");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  return { data, error, loading, refresh, setError };
}

export function VehicleTrackingPage() {
  const state = useFieldOperations();
  const [vehicleId, setVehicleId] = useState("");
  const [logType, setLogType] = useState("fuel");
  const [odometer, setOdometer] = useState("");
  const [litres, setLitres] = useState("");
  const [amount, setAmount] = useState("");
  const [vendor, setVendor] = useState("");
  const [details, setDetails] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!vehicleId) return;
    setSaving(true);
    state.setError(null);
    try {
      const documentIds = await uploadPhotos(files, undefined, "Vehicle receipt or maintenance photo");
      await fieldOperationsApi.createVehicleLog({
        vehicle_id: vehicleId,
        log_type: logType,
        entry_date: today(),
        odometer_km: numberOrNull(odometer),
        litres: numberOrNull(litres),
        amount: numberOrNull(amount),
        vendor: vendor || null,
        details: details || null,
        document_ids: documentIds,
      });
      setOdometer(""); setLitres(""); setAmount(""); setVendor(""); setDetails(""); setFiles([]);
      await state.refresh();
    } catch (current) {
      state.setError(current instanceof Error ? current.message : "Unable to save vehicle log.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <PortalShell title="Vehicle Tracking" eyebrow="Fleet operations" description="Fuel, kilometres, maintenance, receipts and service status for Iron House vehicles." icon={<Truck />}>
      <Status state={state} />
      <div className="grid gap-4 md:grid-cols-2">
        {state.data?.vehicles.map((vehicle) => (
          <article key={vehicle.id} className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-gold-dark">Truck {vehicle.unit_number}</div>
                <h2 className="mt-1 text-xl font-semibold text-iron-950">{vehicle.name}</h2>
                <p className="mt-1 text-sm text-iron-500">Assigned to {vehicle.assigned_driver_name ?? "Unassigned"}</p>
              </div>
              <StatusPill status={vehicle.service_status} />
            </div>
            <div className="mt-5 grid grid-cols-3 gap-3">
              <Fact label="Current km" value={vehicle.current_km.toLocaleString("en-CA")} />
              <Fact label="Next service" value={vehicle.next_service_km?.toLocaleString("en-CA") ?? "Set km"} />
              <Fact label="Service date" value={vehicle.next_service_date ?? "Set date"} />
            </div>
          </article>
        ))}
      </div>
      <form onSubmit={submit} className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
        <SectionTitle icon={<Fuel />} title="Add vehicle entry" subtitle="Attach multiple fuel receipts, invoices or maintenance photos in one entry." />
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <Select label="Vehicle" value={vehicleId} onChange={setVehicleId} required options={state.data?.vehicles.map((item) => [item.id, "Truck " + item.unit_number + " — " + (item.assigned_driver_name ?? item.name)]) ?? []} />
          <Select label="Entry type" value={logType} onChange={setLogType} options={[["fuel", "Fuel"], ["mileage", "Kilometres"], ["maintenance", "Maintenance"], ["inspection", "Inspection"], ["repair", "Repair"]]} />
          <Input label="Odometer (km)" value={odometer} onChange={setOdometer} type="number" />
          <Input label="Litres" value={litres} onChange={setLitres} type="number" />
          <Input label="Cost" value={amount} onChange={setAmount} type="number" />
          <Input label="Vendor" value={vendor} onChange={setVendor} />
          <Input label="Details" value={details} onChange={setDetails} />
          <FilePicker files={files} onChange={setFiles} />
        </div>
        <PrimaryButton disabled={saving || !vehicleId}>{saving ? "Saving…" : "Save vehicle entry"}</PrimaryButton>
      </form>
    </PortalShell>
  );
}

export function ForemanPortalPage() {
  const state = useFieldOperations();
  return (
    <PortalShell title="Foreman Portal" eyebrow="Field command centre" description="Crew time, daily records, vendors, quantities, weather, safety and production evidence." icon={<HardHat />}>
      <Status state={state} />
      {state.data ? (
        <>
          <AlertStrip alerts={state.data.alerts} />
          <JobWorkbookCard data={state.data} onSaved={state.refresh} onError={state.setError} />
          <TimeEntryForm data={state.data} mode="foreman_crew" onSaved={state.refresh} onError={state.setError} />
          <RecordForm data={state.data} mode="foreman" onSaved={state.refresh} onError={state.setError} />
          <ToolboxTalkCard data={state.data} onSaved={state.refresh} onError={state.setError} />
          <RecentRecords records={state.data.records} employees={state.data.employees} onSaved={state.refresh} onError={state.setError} />
        </>
      ) : null}
    </PortalShell>
  );
}

function JobWorkbookCard({ data, onSaved, onError }: { data: FieldOperationsBootstrap; onSaved: () => Promise<void>; onError: (value: string | null) => void }) {
  const [projectId, setProjectId] = useState(data.job_workbooks[0]?.project_id ?? "");
  const items = data.production_items.filter((item) => item.project_id === projectId);
  const [lineKey, setLineKey] = useState(items[0]?.line_key ?? "");
  const [quantity, setQuantity] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const selected = data.production_items.find((item) => item.line_key === lineKey);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!selected || !quantity) return;
    setSaving(true); onError(null);
    try {
      await fieldOperationsApi.createRecord({
        record_type: "material_quantity",
        project_id: selected.project_id,
        cost_code: selected.cost_code,
        work_date: today(),
        title: selected.description,
        details: { line_key: selected.line_key, workbook_id: selected.workbook_id, installed_quantity: Number(quantity), unit: selected.unit, notes },
      });
      setQuantity(""); setNotes(""); await onSaved();
    } catch (current) { onError(current instanceof Error ? current.message : "Unable to save production quantity."); }
    finally { setSaving(false); }
  }

  return (
    <section className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
      <SectionTitle icon={<ClipboardCheck />} title="Job workbook production" subtitle="Compare estimated, installed-to-date and remaining quantities from the latest project estimate." />
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <Select label="Project / job workbook" value={projectId} onChange={(value) => { setProjectId(value); setLineKey(""); }} options={data.job_workbooks.map((book) => { const project = data.projects.find((item) => item.id === book.project_id); return [book.project_id, (project?.name ?? "Project") + " — " + book.line_count + " lines"]; })} />
        <Select label="Production line" value={lineKey} onChange={setLineKey} options={items.map((item) => [item.line_key, (item.cost_code ? item.cost_code + " — " : "") + item.description])} />
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {items.map((item) => <div key={item.line_key} className="rounded-md border border-iron-100 p-3"><div className="text-sm font-semibold text-iron-950">{item.description}</div><div className="mt-1 text-xs text-iron-500">{item.cost_code ?? "No cost code"} · {item.unit}</div><div className="mt-3 grid grid-cols-3 gap-2"><Fact label="Estimate" value={String(item.estimated_quantity)} /><Fact label="Installed" value={String(item.installed_quantity)} /><Fact label="Remaining" value={String(item.remaining_quantity)} /></div><div className="mt-2 text-xs font-semibold text-brand-gold-dark">{item.percent_complete}% complete · {item.materials.length} material(s)</div></div>)}
      </div>
      {selected ? <form onSubmit={submit} className="mt-4 grid gap-3 rounded-md bg-iron-50 p-4 md:grid-cols-3"><Input label={"Installed today (" + selected.unit + ")"} value={quantity} onChange={setQuantity} type="number" required /><Input label="Production notes" value={notes} onChange={setNotes} /><div className="self-end"><PrimaryButton disabled={saving || !quantity}>{saving ? "Saving…" : "Add installed quantity"}</PrimaryButton></div></form> : null}
      {!data.job_workbooks.length ? <div className="mt-4 rounded-md bg-iron-50 p-4 text-sm text-iron-500">Save a project estimate workspace to activate production tracking.</div> : null}
    </section>
  );
}

export function OperatorPortalPage() {
  const state = useFieldOperations();
  return (
    <PortalShell title="Operator Portal" eyebrow="Equipment and time" description="Cost-coded time, machine inspections, service alerts, job photos and employee requests." icon={<Wrench />}>
      <Status state={state} />
      {state.data ? (
        <>
          <AlertStrip alerts={state.data.alerts} />
          <TimeEntryForm data={state.data} mode="operator" onSaved={state.refresh} onError={state.setError} />
          <RecordForm data={state.data} mode="operator" onSaved={state.refresh} onError={state.setError} />
          <RecentRecords records={state.data.records.filter((item) => ["equipment_inspection", "job_photo", "time_off_request", "performance_review"].includes(item.record_type))} employees={state.data.employees} onSaved={state.refresh} onError={state.setError} />
        </>
      ) : null}
    </PortalShell>
  );
}

export function EmployeePortalPage() {
  const state = useFieldOperations();
  return (
    <PortalShell title="Employee Portal" eyebrow="Iron House Contracting" description="Time, daily journal, safety, job photos, requests, contact information and course tickets." icon={<HardHat />}>
      <Status state={state} />
      <SafetyProgramCard />
      {state.data ? (
        <>
          <TimeEntryForm data={state.data} mode="employee" onSaved={state.refresh} onError={state.setError} />
          <RecordForm data={state.data} mode="employee" onSaved={state.refresh} onError={state.setError} />
          <EmployeeDirectory data={state.data} />
          <ToolboxTalkCard data={state.data} onSaved={state.refresh} onError={state.setError} />
          <RecentRecords records={state.data.records} employees={state.data.employees} onSaved={state.refresh} onError={state.setError} />
        </>
      ) : null}
    </PortalShell>
  );
}

function TimeEntryForm({ data, mode, onSaved, onError }: { data: FieldOperationsBootstrap; mode: "employee" | "operator" | "foreman_crew"; onSaved: () => Promise<void>; onError: (value: string | null) => void }) {
  const [employeeId, setEmployeeId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [costCode, setCostCode] = useState("");
  const [regularHours, setRegularHours] = useState("");
  const [overtimeHours, setOvertimeHours] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true); onError(null);
    try {
      await fieldOperationsApi.createTimeEntry({
        employee_id: employeeId, project_id: projectId, cost_code: costCode, work_date: today(),
        regular_hours: Number(regularHours || 0), overtime_hours: Number(overtimeHours || 0),
        entry_type: mode, notes: notes || null,
      });
      setRegularHours(""); setOvertimeHours(""); setNotes("");
      await onSaved();
    } catch (current) { onError(current instanceof Error ? current.message : "Unable to save time."); }
    finally { setSaving(false); }
  }
  return (
    <form onSubmit={submit} className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
      <SectionTitle icon={<Clock3 />} title={mode === "foreman_crew" ? "Crew timesheet" : "Time tracking"} subtitle="Select from the employee, project and Iron House cost-code databases." />
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <Select label="Employee" value={employeeId} onChange={setEmployeeId} required options={employeeOptions(data.employees)} />
        <Select label="Project" value={projectId} onChange={setProjectId} required options={data.projects.map((item) => [item.id, item.name])} />
        <Select label="Cost code" value={costCode} onChange={setCostCode} required options={data.cost_codes.map((item) => [item.code, item.code + " — " + item.name])} />
        <Input label="Regular hours" value={regularHours} onChange={setRegularHours} type="number" />
        <Input label="Overtime hours" value={overtimeHours} onChange={setOvertimeHours} type="number" />
        <Input label="Notes" value={notes} onChange={setNotes} />
      </div>
      <PrimaryButton disabled={saving || !employeeId || !projectId || !costCode}>{saving ? "Saving…" : "Submit time"}</PrimaryButton>
    </form>
  );
}

function RecordForm({ data, mode, onSaved, onError }: { data: FieldOperationsBootstrap; mode: "foreman" | "operator" | "employee"; onSaved: () => Promise<void>; onError: (value: string | null) => void }) {
  const availableTypes = mode === "foreman"
    ? [["journal", "Daily journal"], ["daily_hazard_assessment", "Daily hazard assessment"], ["weather", "Weather"], ["material_quantity", "Material / quantity"], ["subcontractor", "Subcontractor"], ["rental_equipment", "Rental equipment"], ["expense", "Expense"], ["missing_form", "Missing form"], ["job_photo", "Production photos"]]
    : mode === "operator"
      ? [["equipment_inspection", "Machine inspection"], ["job_photo", "Job photos"], ["time_off_request", "Time-off request"], ["performance_review", "Performance review request"], ["journal", "Journal"]]
      : [["journal", "Journal"], ["job_photo", "Job photos"], ["expense", "Expense"], ["missing_form", "Missing form"], ["time_off_request", "Time-off request"], ["performance_review", "Performance review request"]];
  const [recordType, setRecordType] = useState(availableTypes[0][0]);
  const [employeeId, setEmployeeId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [supplierId, setSupplierId] = useState("");
  const [equipmentId, setEquipmentId] = useState("");
  const [costCode, setCostCode] = useState("");
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [severity, setSeverity] = useState("none");
  const [quantity, setQuantity] = useState("");
  const [weather, setWeather] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [attendees, setAttendees] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true); onError(null);
    try {
      const documentIds = await uploadPhotos(files, projectId || undefined, title || recordType);
      await fieldOperationsApi.createRecord({
        record_type: recordType, project_id: projectId || null, employee_id: employeeId || null,
        equipment_id: equipmentId || null, supplier_id: supplierId || null, cost_code: costCode || null,
        work_date: today(), title, severity,
        details: { notes, quantity: quantity || null, weather: weather || null, attendees },
        document_ids: documentIds,
      });
      setTitle(""); setNotes(""); setQuantity(""); setWeather(""); setFiles([]); setAttendees([]); setSeverity("none");
      await onSaved();
    } catch (current) { onError(current instanceof Error ? current.message : "Unable to save field record."); }
    finally { setSaving(false); }
  }
  return (
    <form onSubmit={submit} className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
      <SectionTitle icon={<ClipboardCheck />} title="Field forms and records" subtitle="Photos are stored with the selected job and form. Medium or higher issues alert Jeremie and Mac." />
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <Select label="Form" value={recordType} onChange={setRecordType} options={availableTypes} />
        <Select label="Employee" value={employeeId} onChange={setEmployeeId} options={employeeOptions(data.employees)} />
        <Select label="Project / job" value={projectId} onChange={setProjectId} options={data.projects.map((item) => [item.id, item.name])} />
        <Select label="Cost code" value={costCode} onChange={setCostCode} options={data.cost_codes.map((item) => [item.code, item.code + " — " + item.name])} />
        <Select label="Vendor / subcontractor" value={supplierId} onChange={setSupplierId} options={data.suppliers.map((item) => [item.id, item.name])} />
        <Select label="Machine / rental" value={equipmentId} onChange={setEquipmentId} options={data.equipment.map((item) => [item.id, item.name])} />
        <Input label="Title" value={title} onChange={setTitle} required />
        <Select label="Issue severity" value={severity} onChange={setSeverity} options={[["none", "No issue"], ["low", "Low"], ["medium", "Medium — alert"], ["high", "High — alert"], ["critical", "Critical — alert"]]} />
        <Input label="Quantity / hours / amount" value={quantity} onChange={setQuantity} />
        <Input label="Weather / temperature" value={weather} onChange={setWeather} />
        <Input label="Journal, hazards and controls" value={notes} onChange={setNotes} />
        <FilePicker files={files} onChange={setFiles} />
      </div>
      {["daily_hazard_assessment", "toolbox_talk"].includes(recordType) ? (
        <EmployeeChecklist employees={data.employees} selected={attendees} onChange={setAttendees} />
      ) : null}
      <PrimaryButton disabled={saving || !title}>{saving ? "Saving and uploading…" : "Submit field record"}</PrimaryButton>
    </form>
  );
}

function ToolboxTalkCard({ data, onSaved, onError }: { data: FieldOperationsBootstrap; onSaved: () => Promise<void>; onError: (value: string | null) => void }) {
  const talk = data.toolbox_talk;
  const [attendees, setAttendees] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  async function createTalk() {
    setSaving(true); onError(null);
    try {
      await fieldOperationsApi.createRecord({
        record_type: "toolbox_talk", work_date: today(), title: talk.title,
        details: { summary: talk.summary, discussion_points: talk.discussion_points, source_url: talk.source_url, attendees },
      });
      setAttendees([]); await onSaved();
    } catch (current) { onError(current instanceof Error ? current.message : "Unable to create toolbox talk."); }
    finally { setSaving(false); }
  }
  return (
    <article className="rounded-xl border border-brand-gold/40 bg-white p-5 shadow-sm">
      <SectionTitle icon={<ShieldCheck />} title="Weekly toolbox talk" subtitle={"Week of " + talk.week_of + " · automatically supplied from WorkSafeBC guidance"} />
      <h3 className="mt-4 text-lg font-semibold text-iron-950">{talk.title}</h3>
      <p className="mt-2 text-sm leading-6 text-iron-600">{talk.summary}</p>
      <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-iron-600">{talk.discussion_points.map((point) => <li key={point}>{point}</li>)}</ul>
      <a href={talk.source_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-brand-gold-dark">{talk.source_name}<ExternalLink className="h-3 w-3" /></a>
      <EmployeeChecklist employees={data.employees} selected={attendees} onChange={setAttendees} />
      <button type="button" onClick={() => void createTalk()} disabled={saving} className="mt-4 rounded-md bg-brand-gold px-4 py-2 text-sm font-semibold text-brand-black disabled:opacity-50">{saving ? "Creating…" : "Start talk and collect signatures"}</button>
    </article>
  );
}

function RecentRecords({ records, employees, onSaved, onError }: { records: FieldRecord[]; employees: Employee[]; onSaved: () => Promise<void>; onError: (value: string | null) => void }) {
  const [signer, setSigner] = useState<Record<string, string>>({});
  async function sign(record: FieldRecord) {
    const employeeId = signer[record.id];
    const employee = employees.find((item) => item.id === employeeId);
    if (!employee) return;
    try {
      await fieldOperationsApi.signRecord(record.id, { employee_id: employee.id, employee_name: employee.first_name + " " + employee.last_name });
      await onSaved();
    } catch (current) { onError(current instanceof Error ? current.message : "Unable to sign record."); }
  }
  return (
    <section className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
      <SectionTitle icon={<FileText />} title="Recent field records" subtitle="Open safety and toolbox records remain available for individual digital acknowledgement." />
      <div className="mt-4 grid gap-3">
        {records.slice(0, 12).map((record) => (
          <div key={record.id} className="rounded-md border border-iron-100 p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div><div className="font-semibold text-iron-950">{record.title}</div><div className="mt-1 text-xs uppercase tracking-wide text-iron-500">{record.record_type.replaceAll("_", " ")} · {record.work_date}</div></div>
              <StatusPill status={record.severity} />
            </div>
            <div className="mt-3 text-sm text-iron-600">{String(record.details.notes ?? record.details.summary ?? "")}</div>
            <div className="mt-3 text-xs font-medium text-iron-500">{record.document_ids.length} attachment(s) · {record.signatures.length} signature(s)</div>
            {["daily_hazard_assessment", "toolbox_talk"].includes(record.record_type) ? (
              <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                <select value={signer[record.id] ?? ""} onChange={(event) => setSigner((current) => ({ ...current, [record.id]: event.target.value }))} className="rounded-md border border-iron-100 px-3 py-2 text-sm">
                  <option value="">Select employee signing</option>
                  {employees.map((employee) => <option key={employee.id} value={employee.id}>{employee.first_name} {employee.last_name}</option>)}
                </select>
                <button type="button" onClick={() => void sign(record)} className="rounded-md border border-brand-gold bg-brand-gold/10 px-3 py-2 text-sm font-semibold">Digitally acknowledge</button>
              </div>
            ) : null}
          </div>
        ))}
        {!records.length ? <div className="rounded-md bg-iron-50 p-4 text-sm text-iron-500">No field records have been submitted yet.</div> : null}
      </div>
    </section>
  );
}

function EmployeeDirectory({ data }: { data: FieldOperationsBootstrap }) {
  const certsByEmployee = useMemo(() => new Map(data.employees.map((employee) => [employee.id, data.certifications.filter((item) => item.employee_id === employee.id)])), [data]);
  return (
    <section className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
      <SectionTitle icon={<Users />} title="Employee information and tickets" subtitle="Contact and emergency information is internal. Ticket expiries alert management 60 days ahead." />
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {data.employees.map((employee) => (
          <div key={employee.id} className="rounded-md border border-iron-100 p-4">
            <div className="font-semibold text-iron-950">{employee.first_name} {employee.last_name}</div>
            <div className="mt-1 text-sm text-iron-500">{employee.role ?? employee.portal_role} · {employee.phone ?? "Phone not entered"}</div>
            <div className="mt-2 text-xs text-iron-500">Emergency: {employee.emergency_contact_name ?? "Not entered"} · {employee.emergency_contact_phone ?? "No number"}</div>
            <div className="mt-3 text-xs font-semibold uppercase tracking-wide text-brand-gold-dark">{certsByEmployee.get(employee.id)?.length ?? 0} course ticket(s)</div>
          </div>
        ))}
        {!data.employees.length ? <div className="rounded-md bg-iron-50 p-4 text-sm text-iron-500">Add employees to activate selections, signatures, contacts and expiry alerts.</div> : null}
      </div>
    </section>
  );
}

function SafetyProgramCard() {
  return (
    <article className="rounded-xl border border-brand-gold/40 bg-white p-5 shadow-sm">
      <SectionTitle icon={<BookOpenCheck />} title="Occupational Health, Safety & Environmental Program" subtitle="Controlled Iron House document · British Columbia · Revision 1.1" />
      <p className="mt-3 text-sm leading-6 text-iron-600">Revision 1.1 incorporates current British Columbia and applicable federal safety requirements.</p>
      <a href={SAFETY_PROGRAM_URL} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-2 rounded-md bg-brand-gold px-4 py-2 text-sm font-semibold text-brand-black">Open Safety Program<ExternalLink className="h-4 w-4" /></a>
    </article>
  );
}

function AlertStrip({ alerts }: { alerts: FieldOperationsBootstrap["alerts"] }) {
  if (!alerts.length) return <div className="flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-800"><CheckCircle2 className="h-4 w-4" />No open service, inspection or ticket-expiry alerts.</div>;
  return <div className="rounded-md border border-amber-200 bg-amber-50 p-4"><div className="flex items-center gap-2 font-semibold text-amber-950"><AlertTriangle className="h-4 w-4" />Management alerts</div><ul className="mt-2 space-y-1 text-sm text-amber-900">{alerts.slice(0, 8).map((alert, index) => <li key={alert.title + index}>{alert.title} · {alert.severity}</li>)}</ul></div>;
}

function PortalShell({ title, eyebrow, description, icon, children }: { title: string; eyebrow: string; description: string; icon: ReactNode; children: ReactNode }) {
  return (
    <section className="space-y-6">
      <div className="ihos-brand-surface overflow-hidden rounded-xl border border-brand-gold/30 px-6 py-6 text-white shadow-brand">
        <div className="flex items-center gap-4"><div className="grid h-14 w-14 place-items-center rounded-xl border border-brand-gold/40 bg-white/10 text-brand-gold">{icon}</div><div><div className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-gold">{eyebrow}</div><h1 className="mt-2 text-3xl font-semibold text-brand-silver">{title}</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-iron-100">{description}</p></div></div>
      </div>
      {children}
    </section>
  );
}

function Status({ state }: { state: ReturnType<typeof useFieldOperations> }) {
  if (state.error) return <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">{state.error}</div>;
  if (state.loading) return <div className="flex items-center gap-2 rounded-md border border-iron-100 bg-white p-4 text-sm text-iron-500"><RefreshCw className="h-4 w-4 animate-spin" />Loading field operations…</div>;
  return null;
}
function SectionTitle({ icon, title, subtitle }: { icon: ReactNode; title: string; subtitle: string }) { return <div className="flex gap-3"><div className="mt-0.5 text-brand-gold-dark">{icon}</div><div><h2 className="font-semibold text-iron-950">{title}</h2><p className="mt-1 text-sm text-iron-500">{subtitle}</p></div></div>; }
function Fact({ label, value }: { label: string; value: string }) { return <div className="rounded-md bg-iron-50 p-3"><div className="text-[10px] font-semibold uppercase tracking-wide text-iron-500">{label}</div><div className="mt-1 text-sm font-semibold text-iron-950">{value}</div></div>; }
function StatusPill({ status }: { status: string }) { const danger = ["overdue", "critical", "high"].includes(status); const warning = ["due_soon", "medium"].includes(status); return <span className={"rounded-full px-2.5 py-1 text-xs font-semibold " + (danger ? "bg-red-100 text-red-800" : warning ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800")}>{status.replaceAll("_", " ")}</span>; }
function Input({ label, value, onChange, type = "text", required = false }: { label: string; value: string; onChange: (value: string) => void; type?: string; required?: boolean }) { return <label className="grid gap-1 text-sm"><span className="font-medium text-iron-700">{label}</span><input required={required} type={type} min={type === "number" ? 0 : undefined} step={type === "number" ? "0.01" : undefined} value={value} onChange={(event) => onChange(event.target.value)} className="rounded-md border border-iron-100 px-3 py-2" /></label>; }
function Select({ label, value, onChange, options, required = false }: { label: string; value: string; onChange: (value: string) => void; options: string[][]; required?: boolean }) { return <label className="grid gap-1 text-sm"><span className="font-medium text-iron-700">{label}</span><select required={required} value={value} onChange={(event) => onChange(event.target.value)} className="rounded-md border border-iron-100 px-3 py-2"><option value="">Select…</option>{options.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>; }
function FilePicker({ files, onChange }: { files: File[]; onChange: (value: File[]) => void }) { return <label className="grid gap-1 text-sm"><span className="font-medium text-iron-700">Photos / receipts</span><span className="flex cursor-pointer items-center gap-2 rounded-md border border-dashed border-brand-gold/60 px-3 py-2"><Camera className="h-4 w-4" />{files.length ? files.length + " selected" : "Choose multiple"}<input type="file" accept="image/*,.pdf" multiple capture="environment" className="sr-only" onChange={(event) => onChange(Array.from(event.target.files ?? []))} /></span></label>; }
function PrimaryButton({ children, disabled }: { children: ReactNode; disabled?: boolean }) { return <button type="submit" disabled={disabled} className="mt-4 rounded-md bg-brand-gold px-4 py-2 text-sm font-semibold text-brand-black disabled:opacity-50">{children}</button>; }
function EmployeeChecklist({ employees, selected, onChange }: { employees: Employee[]; selected: string[]; onChange: (value: string[]) => void }) { return <fieldset className="mt-4 rounded-md bg-iron-50 p-4"><legend className="px-1 text-sm font-semibold text-iron-800">Employees attending / required to sign</legend><div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{employees.map((employee) => <label key={employee.id} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={selected.includes(employee.id)} onChange={(event) => onChange(event.target.checked ? [...selected, employee.id] : selected.filter((id) => id !== employee.id))} />{employee.first_name} {employee.last_name}</label>)}</div></fieldset>; }
function employeeOptions(employees: Employee[]): string[][] { return employees.map((item) => [item.id, item.first_name + " " + item.last_name]); }
function numberOrNull(value: string): number | null { return value ? Number(value) : null; }
async function uploadPhotos(files: File[], projectId: string | undefined, description: string): Promise<string[]> { const results = []; for (const file of files) { const uploaded = await documentsApi.upload({ file, title: file.name, category: "photo", project_id: projectId, description }); results.push(uploaded.document.id); } return results; }
