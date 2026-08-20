import { Copy, Download, Plus, QrCode, RefreshCw, ShieldCheck, Truck } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { fieldOperationsApi } from "../api/fieldOperations";
import type { Employee } from "../api/fieldOperations";
import { EquipmentRateLibraryPanel } from "../components/EquipmentRateLibraryPanel";
import { UniversalPhotoField } from "../components/UniversalPhotoField";
import { useAuth } from "../contexts/AuthContext";
import { controlledSafetyProcedures } from "../safetyProcedures";

import {
  Equipment,
  EquipmentCreate,
  EquipmentStatus,
  equipmentApi,
  equipmentStatuses,
} from "../api/equipment";

const money = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" });

export function EquipmentPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<Equipment[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [statusFilter, setStatusFilter] = useState<EquipmentStatus | "">("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const canManageSafetyAssignments = user?.role === "admin" || user?.role === "operations_manager";

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [equipment, fieldOperations] = await Promise.all([
        equipmentApi.list(statusFilter),
        canManageSafetyAssignments ? fieldOperationsApi.bootstrap() : Promise.resolve(null),
      ]);
      setItems(equipment.items);
      setEmployees(fieldOperations?.employees.filter((item) => item.status === "active") ?? []);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to load equipment");
    } finally {
      setIsLoading(false);
    }
  }, [canManageSafetyAssignments, statusFilter]);

  useEffect(() => { void refresh(); }, [refresh]);

  useEffect(() => {
    const equipmentId = new URLSearchParams(window.location.search).get("record");
    if (!isLoading && equipmentId) requestAnimationFrame(() => document.getElementById(`equipment-card-${equipmentId}`)?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }, [isLoading, items]);

  async function create(payload: EquipmentCreate) {
    setError(null);
    try {
      await equipmentApi.create(payload);
      await refresh();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to add equipment");
    }
  }

  async function updateStatus(item: Equipment, status: EquipmentStatus) {
    setError(null);
    try {
      const updated = await equipmentApi.update(item.id, { status });
      setItems((current) => current.map((candidate) => candidate.id === updated.id ? updated : candidate));
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to update equipment");
    }
  }

  async function updateSafetyProcedures(item: Equipment, safetyProcedureCodes: string[]) {
    setError(null);
    try {
      const updated = await equipmentApi.update(item.id, { safety_procedure_codes: safetyProcedureCodes });
      setItems((current) => current.map((candidate) => candidate.id === updated.id ? updated : candidate));
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to update equipment safety procedures");
    }
  }

  async function updateAssignment(item: Equipment, assignedEmployeeId: string) {
    setError(null);
    try {
      const updated = await equipmentApi.update(item.id, { assigned_employee_id: assignedEmployeeId || null });
      setItems((current) => current.map((candidate) => candidate.id === updated.id ? updated : candidate));
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to update equipment assignment");
    }
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-iron-100 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-iron-950">Equipment</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
            Track owned and rental equipment, availability, identifiers, and estimating rates. Iron House remains rental-first and compactors are always rented.
          </p>
        </div>
        <button type="button" onClick={() => void refresh()} className="inline-flex items-center gap-2 rounded-md border border-iron-100 bg-white px-3 py-2 text-sm font-semibold">
          <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} /> Refresh
        </button>
      </div>

      {error ? <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}

      <CreateEquipmentForm onSubmit={create} />

      <EquipmentRateLibraryPanel />

      <div className="rounded-md border border-iron-100 bg-white p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-base font-semibold text-iron-950">Equipment register</h2>
            <p className="mt-1 text-sm text-iron-500">{items.length} matching records</p>
          </div>
          <label className="grid gap-1 text-sm">
            <span className="font-medium text-iron-700">Status filter</span>
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as EquipmentStatus | "")} className="rounded-md border border-iron-100 px-3 py-2">
              <option value="">All statuses</option>
              {equipmentStatuses.map((status) => <option key={status} value={status}>{status.replace("_", " ")}</option>)}
            </select>
          </label>
        </div>

        <div className="mt-4 grid gap-3">
          {items.map((item) => (
            <article id={`equipment-card-${item.id}`} key={item.id} className="scroll-mt-6 grid gap-3 rounded-md border border-iron-100 p-4 md:grid-cols-[1fr_180px_160px] md:items-center">
              <div className="flex gap-3">
                <div className="mt-1 rounded-md bg-iron-950 p-2 text-white"><Truck className="h-4 w-4" /></div>
                <div>
                  <div className="font-semibold text-iron-950">{item.name}</div>
                  <div className="mt-1 text-sm text-iron-500">{item.equipment_type ?? "Unclassified"} · {item.identifier ?? "No identifier"}</div>
                </div>
              </div>
              <div className="text-sm font-semibold text-iron-800">{item.hourly_rate == null ? "Rate not set" : `${money.format(item.hourly_rate)}/hr`}</div>
              <select aria-label={`Status for ${item.name}`} value={item.status} onChange={(event) => void updateStatus(item, event.target.value as EquipmentStatus)} className="rounded-md border border-iron-100 px-3 py-2 text-sm">
                {equipmentStatuses.map((status) => <option key={status} value={status}>{status.replace("_", " ")}</option>)}
              </select>
              <div className="md:col-span-3">
                {canManageSafetyAssignments ? <label className="mb-3 grid max-w-xl gap-1 text-sm"><span className="font-medium text-iron-700">Assigned employee</span><select aria-label={`Assigned employee for ${item.name}`} value={item.assigned_employee_id ?? ""} onChange={(event) => void updateAssignment(item, event.target.value)} className="min-h-11 rounded-md border border-iron-100 px-3 py-2"><option value="">No current assignment</option>{employees.map((employee) => <option key={employee.id} value={employee.id}>{employee.first_name} {employee.last_name}</option>)}</select><span className="text-xs leading-5 text-iron-500">Assignment is one gate only. Operator actions also require Ready orientation controls and approved written and practical qualification evidence.</span></label> : null}
                <div className="flex flex-wrap items-center gap-2 text-sm"><ShieldCheck className="h-4 w-4 text-brand-gold-dark" /><b>Assigned controlled procedures:</b>{item.safety_procedure_codes?.length ? item.safety_procedure_codes.map((code) => <span key={code} className="rounded-full bg-iron-100 px-2 py-1 text-xs font-semibold">{code}</span>) : <span className="text-amber-800">None assigned</span>}</div>
                {canManageSafetyAssignments ? <EquipmentSafetyAssignments item={item} onSave={updateSafetyProcedures} /> : null}
                <EquipmentFieldAccess item={item} />
              </div>
              <div className="md:col-span-3"><UniversalPhotoField recordType="equipment" recordId={item.id} category="equipment" label="Equipment photos and records" /></div>
            </article>
          ))}
          {!isLoading && !items.length ? <div className="rounded-md bg-iron-50 p-5 text-sm text-iron-500">No equipment records match this filter.</div> : null}
        </div>
      </div>
    </section>
  );
}

function CreateEquipmentForm({ onSubmit }: { onSubmit: (payload: EquipmentCreate) => void }) {
  const [name, setName] = useState("");
  const [equipmentType, setEquipmentType] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [hourlyRate, setHourlyRate] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) return;
    onSubmit({
      name: name.trim(),
      equipment_type: equipmentType.trim(),
      identifier: identifier.trim(),
      hourly_rate: hourlyRate ? Number(hourlyRate) : null,
    });
    setName("");
    setEquipmentType("");
    setIdentifier("");
    setHourlyRate("");
  }

  return (
    <form onSubmit={submit} className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex items-center gap-2"><Plus className="h-4 w-4" /><h2 className="text-base font-semibold">Add equipment or rental rate</h2></div>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Input label="Name" value={name} onChange={setName} required />
        <Input label="Type" value={equipmentType} onChange={setEquipmentType} />
        <Input label="Identifier" value={identifier} onChange={setIdentifier} />
        <Input label="Hourly rate" value={hourlyRate} onChange={setHourlyRate} type="number" />
      </div>
      <button type="submit" className="mt-4 rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white">Add to register</button>
    </form>
  );
}

function Input({ label, value, onChange, type = "text", required = false }: { label: string; value: string; onChange: (value: string) => void; type?: string; required?: boolean }) {
  return <label className="grid gap-1 text-sm"><span className="font-medium text-iron-700">{label}</span><input required={required} type={type} min={type === "number" ? 0 : undefined} step={type === "number" ? "0.01" : undefined} value={value} onChange={(event) => onChange(event.target.value)} className="rounded-md border border-iron-100 px-3 py-2" /></label>;
}

function EquipmentSafetyAssignments({ item, onSave }: { item: Equipment; onSave: (item: Equipment, codes: string[]) => Promise<void> }) {
  const [codes, setCodes] = useState(item.safety_procedure_codes ?? []);
  const [saving, setSaving] = useState(false);
  useEffect(() => { setCodes(item.safety_procedure_codes ?? []); }, [item.safety_procedure_codes]);

  async function save() {
    setSaving(true);
    try { await onSave(item, codes); } finally { setSaving(false); }
  }

  return <details className="mt-3 rounded-md border border-iron-100 p-3">
    <summary className="min-h-11 cursor-pointer py-3 text-sm font-semibold">Manage field procedure assignments</summary>
    <div className="grid gap-2 sm:grid-cols-2">{controlledSafetyProcedures.map((procedure) => <label key={procedure.code} className="flex min-h-11 items-start gap-2 rounded-md bg-iron-50 p-3 text-sm"><input type="checkbox" className="mt-1" checked={codes.includes(procedure.code)} onChange={(event) => setCodes((current) => event.target.checked ? [...current, procedure.code] : current.filter((code) => code !== procedure.code))} /><span><b>{procedure.code}</b> · {procedure.title}</span></label>)}</div>
    <p className="mt-3 text-xs leading-5 text-iron-500">Only management-confirmed controlled references are saved. Draft procedures are excluded from assignment.</p>
    <button type="button" disabled={saving} onClick={() => void save()} className="mt-3 min-h-11 rounded-md bg-iron-950 px-4 text-sm font-semibold text-white disabled:opacity-50">{saving ? "Saving…" : "Save procedure assignments"}</button>
  </details>;
}

function EquipmentFieldAccess({ item }: { item: Equipment }) {
  const [open, setOpen] = useState(false);
  const [qrSvg, setQrSvg] = useState("");
  const [qrError, setQrError] = useState("");
  const [copyStatus, setCopyStatus] = useState("");
  const fieldUrl = `${window.location.origin}/equipment/field/${item.id}`;

  useEffect(() => {
    if (!open || qrSvg) return;
    let active = true;
    void import("qrcode")
      .then(({ default: QRCode }) => QRCode.toString(fieldUrl, { type: "svg", errorCorrectionLevel: "M", margin: 1, width: 192, color: { dark: "#0b0d11", light: "#ffffff" } }))
      .then((value) => { if (active) setQrSvg(value); })
      .catch(() => { if (active) setQrError("QR code unavailable. Use Copy field link instead."); });
    return () => { active = false; };
  }, [fieldUrl, open, qrSvg]);

  async function copyLink() {
    try { await navigator.clipboard.writeText(fieldUrl); setCopyStatus("Field link copied."); }
    catch { setCopyStatus("Copy unavailable. Open the field link and copy it from Safari."); }
  }

  const qrDataUrl = qrSvg ? `data:image/svg+xml,${encodeURIComponent(qrSvg)}` : "";
  const name = item.identifier || item.name;
  return <details onToggle={(event) => setOpen(event.currentTarget.open)} className="mt-3 rounded-md border border-brand-gold/30 p-3">
    <summary className="flex min-h-11 cursor-pointer items-center gap-2 py-3 text-sm font-semibold"><QrCode className="h-4 w-4" />Equipment QR field link</summary>
    <div className="flex flex-wrap gap-2"><a href={fieldUrl} className="inline-flex min-h-11 items-center rounded-md bg-iron-950 px-3 text-sm font-semibold text-white">Open field record</a><button type="button" onClick={() => void copyLink()} className="inline-flex min-h-11 items-center gap-2 rounded-md border px-3 text-sm font-semibold"><Copy className="h-4 w-4" />Copy field link</button></div>
    {copyStatus ? <p role="status" className="mt-2 text-xs text-iron-600">{copyStatus}</p> : null}
    <div className="mt-3 flex flex-wrap items-center gap-4">{qrDataUrl ? <><img src={qrDataUrl} alt={`QR field link for ${name}`} className="h-48 w-48 border bg-white p-2" /><a href={qrDataUrl} download={`equipment-${name.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.svg`} className="inline-flex min-h-11 items-center gap-2 rounded-md border border-brand-gold px-3 text-sm font-semibold text-brand-gold-dark"><Download className="h-4 w-4" />Download QR SVG</a></> : <p role={qrError ? "alert" : undefined} className="text-sm text-iron-500">{qrError || "Preparing QR code…"}</p>}</div>
    <p className="mt-2 text-xs leading-5 text-iron-600">The QR contains only an authenticated IHOS equipment URL—no password, token, rate, or safety record content. Sign-in is still required.</p>
  </details>;
}
