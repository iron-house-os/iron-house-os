import { FormEvent, useCallback, useEffect, useState } from "react";

import { CompletedWorkCostLedger, financeApi } from "../api/finance";


const categories = [
  "labour",
  "equipment",
  "material",
  "trucking",
  "subcontract",
  "rental",
  "fuel",
  "other",
] as const;

const money = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" });


export function CompletedWorkCostPanel({ projectId }: { projectId: string }) {
  const [ledger, setLedger] = useState<CompletedWorkCostLedger | null>(null);
  const [selectedLineId, setSelectedLineId] = useState("");
  const [costCode, setCostCode] = useState("");
  const [category, setCategory] = useState("");
  const [amount, setAmount] = useState("");
  const [entryDate, setEntryDate] = useState("");
  const [vendorName, setVendorName] = useState("");
  const [reference, setReference] = useState("");
  const [description, setDescription] = useState("");
  const [pendingKey, setPendingKey] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const next = await financeApi.getCompletedWorkCosts(projectId);
      setLedger(next);
      setSelectedLineId((current) => next.lines.some((line) => line.id === current) ? current : next.lines[0]?.id ?? "");
      setError(null);
    } catch (current) {
      setError(current instanceof Error ? current.message : "Unable to load completed-work actual costs.");
    }
  }, [projectId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  function change(setter: (value: string) => void, value: string) {
    setter(value);
    setPendingKey(null);
    setNotice(null);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!selectedLineId || !costCode || !category || !amount || !entryDate || !description) return;
    const idempotencyKey = pendingKey ?? crypto.randomUUID();
    if (!pendingKey) setPendingKey(idempotencyKey);
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const result = await financeApi.createCompletedWorkCost(projectId, {
        completed_work_id: selectedLineId,
        idempotency_key: idempotencyKey,
        cost_code: costCode,
        category,
        amount: Number(amount),
        entry_date: entryDate,
        vendor_name: vendorName || null,
        reference: reference || null,
        description,
      });
      setNotice(result.idempotent ? "Exact retry confirmed; no duplicate cost was created." : "Verified internal actual cost recorded.");
      setCostCode("");
      setCategory("");
      setAmount("");
      setEntryDate("");
      setVendorName("");
      setReference("");
      setDescription("");
      setPendingKey(null);
      await refresh();
    } catch (current) {
      setError(current instanceof Error ? current.message : "Unable to record the completed-work actual cost.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section aria-label="Completed-work actual costs" className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-base font-semibold text-iron-950">Completed-work actual costs</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
            Link verified internal costs to their exact completed-work source line for cost-code traceability.
          </p>
        </div>
        {ledger ? (
          <div className="grid grid-cols-2 gap-2 text-right text-xs text-iron-600">
            <span>{ledger.linked_line_count} of {ledger.source_line_count} lines linked</span>
            <span>{money.format(ledger.linked_actual_cost_total)} linked actual</span>
          </div>
        ) : null}
      </div>

      {ledger ? (
        <p className="mt-4 rounded-md border border-brand-gold/40 bg-brand-gold/10 p-3 text-sm leading-6 text-iron-800">
          {ledger.warning}
        </p>
      ) : null}
      {error ? <p role="alert" className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      {notice ? <p role="status" className="mt-4 rounded-md bg-signal-green/10 p-3 text-sm text-signal-green">{notice}</p> : null}

      {ledger?.lines.length ? (
        <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(340px,0.8fr)]">
          <div className="overflow-x-auto rounded-md border border-iron-100">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-iron-100 bg-iron-50 text-xs uppercase tracking-wide text-iron-500">
                  <th className="p-3">Completed-work source</th>
                  <th className="p-3">Revenue evidence</th>
                  <th className="p-3">Linked internal actual</th>
                </tr>
              </thead>
              <tbody>
                {ledger.lines.map((line) => (
                  <tr key={line.id} className="border-b border-iron-100 align-top last:border-b-0">
                    <td className="p-3">
                      <div className="font-semibold text-iron-950">{line.description}</div>
                      <div className="mt-1 text-xs text-iron-500">{line.source_invoice_number ?? line.source_import_key} · {line.work_date}</div>
                    </td>
                    <td className="p-3 text-iron-700">
                      {line.quantity} {line.unit} × {money.format(Number(line.billable_rate))}
                      <div className="font-semibold text-iron-950">{money.format(Number(line.billable_amount))}</div>
                    </td>
                    <td className="p-3 text-iron-700">
                      <div className="font-semibold text-iron-950">{money.format(line.linked_actual_cost_total)}</div>
                      {line.linked_entries.length ? (
                        <ul className="mt-1 space-y-1 text-xs text-iron-500">
                          {line.linked_entries.map((entry) => (
                            <li key={entry.id}>{entry.cost_code} · {entry.category} · {money.format(Number(entry.amount))}</li>
                          ))}
                        </ul>
                      ) : <span className="text-xs">No internal actual cost linked</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <form onSubmit={submit} className="rounded-md border border-iron-100 p-4">
            <h3 className="text-sm font-semibold text-iron-950">Record verified internal actual cost</h3>
            <p className="mt-1 text-xs leading-5 text-iron-500">Enter the cost from verified payroll, equipment, receipt, invoice, or accounting evidence. No billable value is copied.</p>
            <div className="mt-4 space-y-3">
              <Field label="Completed-work source line">
                <select aria-label="Completed-work source line" required value={selectedLineId} onChange={(event) => change(setSelectedLineId, event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm">
                  {ledger.lines.map((line) => <option key={line.id} value={line.id}>{line.description} · {line.source_invoice_number ?? line.source_line_key}</option>)}
                </select>
              </Field>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Cost code">
                  <input aria-label="Cost code" required maxLength={32} value={costCode} onChange={(event) => change(setCostCode, event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" />
                </Field>
                <Field label="Cost category">
                  <select aria-label="Cost category" required value={category} onChange={(event) => change(setCategory, event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm">
                    <option value="">Select category</option>
                    {categories.map((item) => <option key={item} value={item}>{title(item)}</option>)}
                  </select>
                </Field>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Actual cost (CAD)">
                  <input aria-label="Actual cost (CAD)" required type="number" min="0.01" max="999999999" step="0.01" value={amount} onChange={(event) => change(setAmount, event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" />
                </Field>
                <Field label="Cost entry date">
                  <input aria-label="Cost entry date" required type="date" value={entryDate} onChange={(event) => change(setEntryDate, event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" />
                </Field>
              </div>
              <Field label="Evidence description">
                <textarea aria-label="Evidence description" required maxLength={2000} rows={2} value={description} onChange={(event) => change(setDescription, event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" />
              </Field>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Reference (if known)">
                  <input aria-label="Reference (if known)" maxLength={120} value={reference} onChange={(event) => change(setReference, event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" />
                </Field>
                <Field label="Vendor / payee (if known)">
                  <input aria-label="Vendor / payee (if known)" maxLength={255} value={vendorName} onChange={(event) => change(setVendorName, event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" />
                </Field>
              </div>
              <button disabled={saving} className="inline-flex min-h-11 items-center rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60">
                {saving ? "Recording..." : "Record explicit actual cost"}
              </button>
            </div>
          </form>
        </div>
      ) : ledger ? (
        <p className="mt-4 rounded-md border border-iron-100 bg-iron-50 p-4 text-sm text-iron-600">No completed-work source records are available for cost linkage.</p>
      ) : null}
    </section>
  );
}


function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block text-xs font-semibold text-iron-700"><span className="mb-1 block">{label}</span>{children}</label>;
}


function title(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
