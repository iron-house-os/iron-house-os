import { FormEvent, useEffect, useMemo, useState } from "react";

import { fieldOperationsApi, FieldOperationsBootstrap, FieldRecord } from "../api/fieldOperations";
import { useAuth } from "../contexts/AuthContext";

const today = () => new Date().toISOString().slice(0, 10);

function buildPoNumber(jobNumber: string) {
  const sequence = Date.now().toString().slice(-8);
  return `PO-${sequence}-${jobNumber}`;
}

export function PurchaseOrderRequestPage() {
  const { user, portalRole } = useAuth();
  const [data, setData] = useState<FieldOperationsBootstrap | null>(null);
  const [projectId, setProjectId] = useState("");
  const [supplierId, setSupplierId] = useState("");
  const [costCode, setCostCode] = useState("");
  const [purpose, setPurpose] = useState("");
  const [amount, setAmount] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdPo, setCreatedPo] = useState<string | null>(null);

  async function refresh() {
    setError(null);
    try {
      setData(await fieldOperationsApi.bootstrap());
    } catch (current) {
      setError(current instanceof Error ? current.message : "Unable to load PO request data.");
    }
  }

  useEffect(() => { void refresh(); }, []);

  const selectedProject = data?.projects.find((project) => project.id === projectId);
  const selectedSupplier = data?.suppliers.find((supplier) => supplier.id === supplierId);
  const pending = useMemo(
    () => (data?.records ?? []).filter((record) => record.record_type === "purchase_order_request"),
    [data],
  );

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!selectedProject || !purpose.trim()) return;
    const jobNumber = String(selectedProject.project_number ?? selectedProject.name).trim();
    const poNumber = buildPoNumber(jobNumber);
    setSaving(true);
    setError(null);
    try {
      await fieldOperationsApi.createRecord({
        record_type: "purchase_order_request",
        project_id: selectedProject.id,
        supplier_id: supplierId || null,
        cost_code: costCode || null,
        work_date: today(),
        title: `${poNumber} — ${purpose.trim()}`,
        status: "pending_approval",
        details: {
          po_number: poNumber,
          job_number: jobNumber,
          supplier_name: selectedSupplier?.name ?? null,
          purpose: purpose.trim(),
          amount_estimate: amount ? Number(amount) : null,
          requester_role: portalRole ?? user?.role ?? "management",
          requested_by: user?.email ?? null,
          requested_at: new Date().toISOString(),
        },
      });
      setCreatedPo(poNumber);
      setPurpose("");
      setAmount("");
      setSupplierId("");
      setCostCode("");
      await refresh();
    } catch (current) {
      setError(current instanceof Error ? current.message : "Unable to create PO request.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="space-y-6">
      <div className="rounded-xl border border-brand-gold/30 bg-iron-950 p-6 text-white shadow-brand">
        <div className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-gold">Purchasing control</div>
        <h1 className="mt-2 text-3xl font-semibold">Request PO</h1>
        <p className="mt-2 max-w-3xl text-sm text-iron-200">
          Select the job and purchase details. IHOS generates the PO automatically with the PO identifier first and the job number appended.
        </p>
      </div>

      {error ? <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
      {createdPo ? <div className="rounded-md border border-green-200 bg-green-50 p-4 text-sm font-semibold text-green-800">Created {createdPo} and sent for approval.</div> : null}

      <form onSubmit={submit} className="grid gap-4 rounded-xl border border-iron-100 bg-white p-5 shadow-sm md:grid-cols-2">
        <label className="grid gap-2 text-sm font-medium text-iron-800">
          Job
          <select required value={projectId} onChange={(event) => setProjectId(event.target.value)} className="rounded-md border border-iron-200 px-3 py-2">
            <option value="">Select job</option>
            {data?.projects.map((project) => <option key={project.id} value={project.id}>{String(project.project_number ?? "")} {project.name}</option>)}
          </select>
        </label>
        <label className="grid gap-2 text-sm font-medium text-iron-800">
          Supplier / vendor
          <select value={supplierId} onChange={(event) => setSupplierId(event.target.value)} className="rounded-md border border-iron-200 px-3 py-2">
            <option value="">Not selected</option>
            {data?.suppliers.map((supplier) => <option key={supplier.id} value={supplier.id}>{supplier.name}</option>)}
          </select>
        </label>
        <label className="grid gap-2 text-sm font-medium text-iron-800">
          Cost code
          <select value={costCode} onChange={(event) => setCostCode(event.target.value)} className="rounded-md border border-iron-200 px-3 py-2">
            <option value="">Not selected</option>
            {data?.cost_codes.map((item) => <option key={item.code} value={item.code}>{item.code} — {item.name}</option>)}
          </select>
        </label>
        <label className="grid gap-2 text-sm font-medium text-iron-800">
          Estimated amount
          <input type="number" step="0.01" min="0" value={amount} onChange={(event) => setAmount(event.target.value)} className="rounded-md border border-iron-200 px-3 py-2" />
        </label>
        <label className="grid gap-2 text-sm font-medium text-iron-800 md:col-span-2">
          Purchase purpose / items needed
          <textarea required value={purpose} onChange={(event) => setPurpose(event.target.value)} className="min-h-28 rounded-md border border-iron-200 px-3 py-2" placeholder="Example: 20 m of 200 mm PVC, fittings and bedding material" />
        </label>
        <div className="md:col-span-2">
          <button disabled={saving || !projectId || !purpose.trim()} className="rounded-md bg-brand-gold px-4 py-2 font-semibold text-brand-black disabled:opacity-50">
            {saving ? "Creating PO…" : "Request PO"}
          </button>
        </div>
      </form>

      <section className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-iron-950">PO request queue</h2>
        <p className="mt-1 text-sm text-iron-500">Submitted requests remain pending until management approval.</p>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-iron-50 text-xs uppercase tracking-wide text-iron-500"><tr><th className="px-3 py-2">PO</th><th className="px-3 py-2">Job</th><th className="px-3 py-2">Purpose</th><th className="px-3 py-2">Status</th></tr></thead>
            <tbody>{pending.slice(0, 25).map((record: FieldRecord) => <tr key={record.id} className="border-t border-iron-100"><td className="px-3 py-2 font-semibold text-iron-950">{String(record.details.po_number ?? "—")}</td><td className="px-3 py-2">{String(record.details.job_number ?? "—")}</td><td className="px-3 py-2">{String(record.details.purpose ?? record.title)}</td><td className="px-3 py-2">{record.status.replaceAll("_", " ")}</td></tr>)}</tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
