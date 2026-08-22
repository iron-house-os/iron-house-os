import { FormEvent, useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";

import { fieldOperationsApi, FieldOperationsBootstrap, FieldRecord } from "../api/fieldOperations";
import { documentsApi } from "../api/documents";
import { useAuth } from "../contexts/AuthContext";
import { DraftSaveIndicator } from "../components/DraftSaveIndicator";
import { useWorkflowDraft } from "../hooks/useWorkflowDraft";
import { readEffectiveProjectContext } from "../utils/projectContext";

const today = () => new Date().toISOString().slice(0, 10);

function buildPoNumber(jobNumber: string) {
  const sequence = Date.now().toString().slice(-8);
  return `PO-${sequence}-${jobNumber}`;
}

export function PurchaseOrderRequestPage() {
  const { user, portalRole } = useAuth();
  const location = useLocation();
  const routedProjectId = readEffectiveProjectContext(location.search).projectId ?? "";
  const requestedDraftId = new URLSearchParams(location.search).get("draftId");
  const [data, setData] = useState<FieldOperationsBootstrap | null>(null);
  const [projectId, setProjectId] = useState(routedProjectId);
  const [supplierId, setSupplierId] = useState("");
  const [costCode, setCostCode] = useState("");
  const [purpose, setPurpose] = useState("");
  const [amount, setAmount] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdPo, setCreatedPo] = useState<string | null>(null);
  const [bootstrapReady, setBootstrapReady] = useState(false);
  const [invoicePoId, setInvoicePoId] = useState("");
  const [invoiceFile, setInvoiceFile] = useState<File | null>(null);
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [invoiceVendor, setInvoiceVendor] = useState("");
  const [invoiceDate, setInvoiceDate] = useState(today());
  const [invoiceSubtotal, setInvoiceSubtotal] = useState("");
  const [invoiceTax, setInvoiceTax] = useState("");
  const [invoiceTotal, setInvoiceTotal] = useState("");
  const [invoiceNote, setInvoiceNote] = useState("");
  const [invoiceFilter, setInvoiceFilter] = useState("pending_approval");
  const [invoiceMessage, setInvoiceMessage] = useState<string | null>(null);

  async function refresh() {
    setError(null);
    try {
      setData(await fieldOperationsApi.bootstrap());
    } catch (current) {
      setError(current instanceof Error ? current.message : "Unable to load PO request data.");
    }
  }

  useEffect(() => {
    void refresh().finally(() => setBootstrapReady(true));
  }, []);
  useEffect(() => {
    if (!bootstrapReady || requestedDraftId || !routedProjectId) return;
    if (!data?.projects.some((project) => project.id === routedProjectId)) return;
    setProjectId(routedProjectId);
  }, [bootstrapReady, data?.projects, requestedDraftId, routedProjectId]);

  const draftPayload = useMemo(() => ({
    projectId,
    supplierId,
    costCode,
    purpose,
    amount,
  }), [amount, costCode, projectId, purpose, supplierId]);
  const draftEnabled = Boolean(projectId || supplierId || costCode || purpose.trim() || amount);
  const draft = useWorkflowDraft({
    workflowType: "purchase_order_request",
    title: purpose.trim() ? `PO request — ${purpose.trim().slice(0, 80)}` : "Purchase order request",
    payload: draftPayload,
    projectId: projectId || null,
    ready: bootstrapReady,
    enabled: draftEnabled,
    onRestore: (saved) => {
      setProjectId(requestedDraftId
        ? (typeof saved.projectId === "string" ? saved.projectId : "")
        : routedProjectId || (typeof saved.projectId === "string" ? saved.projectId : ""));
      setSupplierId(typeof saved.supplierId === "string" ? saved.supplierId : "");
      setCostCode(typeof saved.costCode === "string" ? saved.costCode : "");
      setPurpose(typeof saved.purpose === "string" ? saved.purpose : "");
      setAmount(typeof saved.amount === "string" ? saved.amount : "");
    },
  });

  const selectedProject = data?.projects.find((project) => project.id === projectId);
  const selectedSupplier = data?.suppliers.find((supplier) => supplier.id === supplierId);
  const pending = useMemo(
    () => (data?.records ?? []).filter((record) => record.record_type === "purchase_order_request"),
    [data],
  );
  const selectedInvoicePo = pending.find((record) => record.id === invoicePoId);
  const invoiceQueue = pending.filter((record) => invoiceFilter === "all" || String(record.details.invoice_status ?? "not_attached") === invoiceFilter);
  const canReviewInvoices = user?.role === "admin" || user?.role === "operations_manager";

  async function attachInvoice(event: FormEvent) {
    event.preventDefault();
    if (!selectedInvoicePo || !invoiceFile) return;
    setSaving(true); setError(null); setInvoiceMessage(null);
    try {
      const uploaded = await documentsApi.upload({ file: invoiceFile, title: `${invoiceNumber.trim()} — ${String(selectedInvoicePo.details.po_number ?? selectedInvoicePo.title)}`, category: "other", project_id: selectedInvoicePo.project_id ?? undefined, description: "Supplier invoice attached to purchase order" });
      await fieldOperationsApi.attachPoInvoice(selectedInvoicePo.id, { document_id: uploaded.document.id, invoice_number: invoiceNumber.trim(), vendor_name: invoiceVendor.trim(), invoice_date: invoiceDate, subtotal: Number(invoiceSubtotal), tax: Number(invoiceTax), total: Number(invoiceTotal), note: invoiceNote.trim() || null });
      setInvoiceMessage(`Invoice ${invoiceNumber.trim()} attached and awaiting administrator approval.`);
      setInvoiceFile(null); setInvoiceNumber(""); setInvoiceVendor(""); setInvoiceDate(today()); setInvoiceSubtotal(""); setInvoiceTax(""); setInvoiceTotal(""); setInvoiceNote("");
      await refresh();
    } catch (current) { setError(current instanceof Error ? current.message : "Unable to attach invoice."); }
    finally { setSaving(false); }
  }

  async function decideInvoice(record: FieldRecord, decision: "approved" | "rejected") {
    const note = window.prompt(decision === "rejected" ? "Rejection reason (required)" : "Approval note (optional)", "");
    if (note === null || (decision === "rejected" && !note.trim())) return;
    setSaving(true); setError(null); setInvoiceMessage(null);
    try { await fieldOperationsApi.decidePoInvoice(record.id, decision, note); setInvoiceMessage(`Invoice ${decision}. No payment or accounting entry was created.`); await refresh(); }
    catch (current) { setError(current instanceof Error ? current.message : "Unable to record invoice decision."); }
    finally { setSaving(false); }
  }

  async function openInvoice(documentId: string) {
    try { const token = await documentsApi.requestDownloadToken(documentId); window.open(documentsApi.signedDownloadUrl(token.token), "_blank", "noopener,noreferrer"); }
    catch (current) { setError(current instanceof Error ? current.message : "Unable to open invoice attachment."); }
  }

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
      await draft.completeDraft();
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

      <DraftSaveIndicator status={draft.status} lastSavedAt={draft.lastSavedAt} />

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

      <section className="rounded-xl border border-brand-gold/40 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><div className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-gold-dark">Finance control</div><h2 className="mt-1 text-xl font-semibold text-iron-950">PO invoice approval</h2><p className="mt-1 text-sm text-iron-500">Attach the supplier invoice to its PO. Administrator approval records the decision only; it does not pay or export the invoice.</p></div>
          <label className="grid gap-1 text-sm font-medium text-iron-700">Queue filter<select value={invoiceFilter} onChange={(event) => setInvoiceFilter(event.target.value)} className="rounded-md border border-iron-200 px-3 py-2"><option value="pending_approval">Pending approval</option><option value="approved">Approved</option><option value="rejected">Rejected</option><option value="not_attached">Not attached</option><option value="all">All</option></select></label>
        </div>
        {invoiceMessage ? <div className="mt-4 rounded-md border border-green-200 bg-green-50 p-3 text-sm font-semibold text-green-800">{invoiceMessage}</div> : null}
        <form onSubmit={attachInvoice} className="mt-5 grid gap-3 rounded-lg border border-iron-100 bg-iron-50 p-4 md:grid-cols-3">
          <label className="grid gap-1 text-sm font-medium">PO number<select required value={invoicePoId} onChange={(event) => { const id = event.target.value; setInvoicePoId(id); const record = pending.find((item) => item.id === id); setInvoiceVendor(String(record?.details.supplier_name ?? "")); }} className="rounded-md border border-iron-200 bg-white px-3 py-2"><option value="">Select PO</option>{pending.map((record) => <option key={record.id} value={record.id}>{String(record.details.po_number ?? record.title)} — {String(record.details.job_number ?? "No job")}</option>)}</select></label>
          <label className="grid gap-1 text-sm font-medium">Invoice number<input required value={invoiceNumber} onChange={(event) => setInvoiceNumber(event.target.value)} className="rounded-md border border-iron-200 px-3 py-2" /></label>
          <label className="grid gap-1 text-sm font-medium">Vendor<input required value={invoiceVendor} onChange={(event) => setInvoiceVendor(event.target.value)} className="rounded-md border border-iron-200 px-3 py-2" /></label>
          <label className="grid gap-1 text-sm font-medium">Invoice date<input required type="date" value={invoiceDate} onChange={(event) => setInvoiceDate(event.target.value)} className="rounded-md border border-iron-200 px-3 py-2" /></label>
          <label className="grid gap-1 text-sm font-medium">Subtotal<input required type="number" min="0" step="0.01" value={invoiceSubtotal} onChange={(event) => setInvoiceSubtotal(event.target.value)} className="rounded-md border border-iron-200 px-3 py-2" /></label>
          <label className="grid gap-1 text-sm font-medium">Tax<input required type="number" min="0" step="0.01" value={invoiceTax} onChange={(event) => setInvoiceTax(event.target.value)} className="rounded-md border border-iron-200 px-3 py-2" /></label>
          <label className="grid gap-1 text-sm font-medium">Total<input required type="number" min="0.01" step="0.01" value={invoiceTotal} onChange={(event) => setInvoiceTotal(event.target.value)} className="rounded-md border border-iron-200 px-3 py-2" /></label>
          <label className="grid gap-1 text-sm font-medium md:col-span-2">Invoice PDF or image<input required type="file" accept="application/pdf,image/*" onChange={(event) => setInvoiceFile(event.target.files?.[0] ?? null)} className="rounded-md border border-iron-200 bg-white px-3 py-2" /></label>
          <label className="grid gap-1 text-sm font-medium md:col-span-3">Note<input value={invoiceNote} onChange={(event) => setInvoiceNote(event.target.value)} className="rounded-md border border-iron-200 px-3 py-2" /></label>
          {selectedInvoicePo ? <div className="text-sm text-iron-600 md:col-span-3">Linked job: <strong>{String(selectedInvoicePo.details.job_number ?? "—")}</strong> · PO requested amount: <strong>${Number(selectedInvoicePo.details.amount_estimate ?? 0).toFixed(2)}</strong> · Invoice variance: <strong>${(Number(invoiceTotal || 0) - Number(selectedInvoicePo.details.amount_estimate ?? 0)).toFixed(2)}</strong></div> : null}
          <div className="md:col-span-3"><button disabled={saving || !invoicePoId || !invoiceFile} className="rounded-md bg-iron-950 px-4 py-2 font-semibold text-white disabled:opacity-50">{saving ? "Saving…" : "Attach invoice for approval"}</button></div>
        </form>
        <div className="mt-5 space-y-3">{invoiceQueue.map((record) => { const invoice = (record.details.invoice ?? {}) as Record<string, unknown>; const status = String(record.details.invoice_status ?? "not_attached"); const duplicates = (invoice.duplicate_po_numbers ?? []) as string[]; const variance = Number(invoice.total ?? 0) - Number(record.details.amount_estimate ?? 0); return <article key={record.id} className="rounded-lg border border-iron-100 p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="font-semibold text-iron-950">{String(record.details.po_number ?? record.title)} · {String(record.details.job_number ?? "—")}</div><div className="mt-1 text-sm text-iron-600">{invoice.invoice_number ? `${String(invoice.vendor_name)} invoice ${String(invoice.invoice_number)} · $${Number(invoice.total).toFixed(2)} · variance $${variance.toFixed(2)}` : "No invoice attached"}</div></div><span className="rounded-full bg-iron-100 px-2 py-1 text-xs font-semibold uppercase tracking-wide text-iron-700">{status.replaceAll("_", " ")}</span></div>{duplicates.length ? <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-900">Possible duplicate vendor + invoice number on {duplicates.join(", ")}.</div> : null}{invoice.document_id ? <div className="mt-3 flex flex-wrap gap-2"><button type="button" onClick={() => void openInvoice(String(invoice.document_id))} className="rounded-md border border-iron-200 px-3 py-2 text-sm font-semibold">Open invoice attachment</button>{canReviewInvoices && status === "pending_approval" ? <><button type="button" disabled={saving} onClick={() => void decideInvoice(record, "approved")} className="rounded-md bg-brand-gold px-3 py-2 text-sm font-semibold text-brand-black">Approve invoice</button><button type="button" disabled={saving} onClick={() => void decideInvoice(record, "rejected")} className="rounded-md border border-red-200 px-3 py-2 text-sm font-semibold text-red-700">Reject</button></> : null}</div> : null}<div className="mt-3 text-xs text-iron-500">Audit events: {Array.isArray(record.details.invoice_audit_history) ? record.details.invoice_audit_history.length : 0}</div></article>; })}</div>
      </section>
    </section>
  );
}
