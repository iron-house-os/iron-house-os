import { Plus, RefreshCw, Truck } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  Equipment,
  EquipmentCreate,
  EquipmentStatus,
  equipmentApi,
  equipmentStatuses,
} from "../api/equipment";

const money = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" });

export function EquipmentPage() {
  const [items, setItems] = useState<Equipment[]>([]);
  const [statusFilter, setStatusFilter] = useState<EquipmentStatus | "">("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setItems((await equipmentApi.list(statusFilter)).items);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to load equipment");
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { void refresh(); }, [refresh]);

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
            <div key={item.id} className="grid gap-3 rounded-md border border-iron-100 p-4 md:grid-cols-[1fr_180px_160px] md:items-center">
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
            </div>
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
