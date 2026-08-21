import { ArrowRight, CheckCircle2, Plus, Trash2 } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import {
  CustomerQuote,
  CustomerQuoteInput,
  CustomerQuoteLineItem,
  customerQuotesApi,
} from "../api/customerQuotes";
import { DraftSaveIndicator } from "../components/DraftSaveIndicator";
import { useAuth } from "../contexts/AuthContext";
import { useWorkflowDraft } from "../hooks/useWorkflowDraft";

const money = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" });
const today = () => new Date().toISOString().slice(0, 10);
const blankLine = (): CustomerQuoteLineItem => ({ description: "", quantity: "1", unit: "LS", unit_price: "" });

export function CustomerQuotesPage() {
  const { user } = useAuth();
  const [quotes, setQuotes] = useState<CustomerQuote[]>([]);
  const [registerReady, setRegisterReady] = useState(false);
  const [editing, setEditing] = useState<CustomerQuote | null>(null);
  const [projectName, setProjectName] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");
  const [siteAddress, setSiteAddress] = useState("");
  const [scopeSummary, setScopeSummary] = useState("");
  const [lineItems, setLineItems] = useState<CustomerQuoteLineItem[]>([blankLine()]);
  const [assumptions, setAssumptions] = useState("");
  const [exclusions, setExclusions] = useState("");
  const [gstRate, setGstRate] = useState("5.00");
  const [quoteDate, setQuoteDate] = useState(today());
  const [validUntil, setValidUntil] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedQuote, setSavedQuote] = useState<CustomerQuote | null>(null);
  const [accepting, setAccepting] = useState<CustomerQuote | null>(null);
  const [acceptanceReference, setAcceptanceReference] = useState("");
  const [acceptanceNote, setAcceptanceNote] = useState("");

  async function refresh() {
    try {
      const result = await customerQuotesApi.list();
      setQuotes(result.items);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load customer quotes.");
    } finally {
      setRegisterReady(true);
    }
  }

  useEffect(() => { void refresh(); }, []);

  const draftPayload = useMemo(() => ({
    projectName,
    customerName,
    customerEmail,
    customerPhone,
    siteAddress,
    scopeSummary,
    lineItems,
    assumptions,
    exclusions,
    gstRate,
    quoteDate,
    validUntil,
    notes,
  }), [assumptions, customerEmail, customerName, customerPhone, exclusions, gstRate, lineItems, notes, projectName, quoteDate, scopeSummary, siteAddress, validUntil]);
  const draftEnabled = Boolean(
    projectName.trim() || customerName.trim() || customerEmail.trim() || customerPhone.trim() ||
    siteAddress.trim() || scopeSummary.trim() || notes.trim() || assumptions.trim() || exclusions.trim() ||
    lineItems.some((line) => line.description.trim() || Number(line.unit_price) > 0),
  );
  const draft = useWorkflowDraft({
    workflowType: "customer_quote",
    title: customerName.trim() ? `Customer quote — ${customerName.trim()}` : "Customer quote",
    payload: draftPayload,
    ready: registerReady,
    enabled: draftEnabled && !editing,
    onRestore: (saved) => {
      setProjectName(text(saved.projectName));
      setCustomerName(text(saved.customerName));
      setCustomerEmail(text(saved.customerEmail));
      setCustomerPhone(text(saved.customerPhone));
      setSiteAddress(text(saved.siteAddress));
      setScopeSummary(text(saved.scopeSummary));
      if (Array.isArray(saved.lineItems) && saved.lineItems.length) setLineItems(saved.lineItems as CustomerQuoteLineItem[]);
      setAssumptions(text(saved.assumptions));
      setExclusions(text(saved.exclusions));
      setGstRate(text(saved.gstRate) || "5.00");
      setQuoteDate(text(saved.quoteDate) || today());
      setValidUntil(text(saved.validUntil));
      setNotes(text(saved.notes));
    },
  });

  const totals = useMemo(() => {
    const subtotal = lineItems.reduce(
      (sum, line) => sum + (Number(line.quantity) || 0) * (Number(line.unit_price) || 0),
      0,
    );
    const gst = subtotal * (Number(gstRate) || 0) / 100;
    return { subtotal, gst, total: subtotal + gst };
  }, [gstRate, lineItems]);

  function input(): CustomerQuoteInput {
    return {
      project_name: projectName.trim(),
      customer_name: customerName.trim(),
      customer_email: customerEmail.trim() || null,
      customer_phone: customerPhone.trim() || null,
      site_address: siteAddress.trim() || null,
      scope_summary: scopeSummary.trim(),
      line_items: lineItems.map((line) => ({
        description: line.description.trim(),
        quantity: String(Number(line.quantity) || 0),
        unit: line.unit.trim() || "LS",
        unit_price: String(Number(line.unit_price) || 0),
      })),
      assumptions: lines(assumptions),
      exclusions: lines(exclusions),
      gst_rate: String(Number(gstRate) || 0),
      quote_date: quoteDate,
      valid_until: validUntil || null,
      notes: notes.trim() || null,
    };
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const result = editing
        ? await customerQuotesApi.update(editing.id, editing.record_revision, input())
        : await customerQuotesApi.create(input());
      if (!editing) await draft.completeDraft();
      setSavedQuote(result);
      setQuotes((current) => [result, ...current.filter((quote) => quote.id !== result.id)]);
      reset();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to save the customer quote.");
    } finally {
      setSaving(false);
    }
  }

  function edit(quote: CustomerQuote) {
    setEditing(quote);
    setProjectName(quote.project_name);
    setCustomerName(quote.customer_name);
    setCustomerEmail(quote.customer_email ?? "");
    setCustomerPhone(quote.customer_phone ?? "");
    setSiteAddress(quote.site_address ?? "");
    setScopeSummary(quote.scope_summary);
    setLineItems(quote.line_items.map((line) => ({ ...line, amount: undefined })));
    setAssumptions(quote.assumptions.join("\n"));
    setExclusions(quote.exclusions.join("\n"));
    setGstRate(quote.gst_rate);
    setQuoteDate(quote.quote_date);
    setValidUntil(quote.valid_until ?? "");
    setNotes(quote.notes ?? "");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function reset() {
    setEditing(null);
    setProjectName("");
    setCustomerName("");
    setCustomerEmail("");
    setCustomerPhone("");
    setSiteAddress("");
    setScopeSummary("");
    setLineItems([blankLine()]);
    setAssumptions("");
    setExclusions("");
    setGstRate("5.00");
    setQuoteDate(today());
    setValidUntil("");
    setNotes("");
  }

  async function markSent(quote: CustomerQuote) {
    setError(null);
    try {
      const result = await customerQuotesApi.status(quote.id, quote.record_revision, "sent");
      setQuotes((current) => current.map((item) => item.id === result.id ? result : item));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to update quote status.");
    }
  }

  async function accept() {
    if (!accepting || !acceptanceReference.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const result = await customerQuotesApi.accept(
        accepting.id,
        accepting.record_revision,
        acceptanceReference.trim(),
        acceptanceNote.trim(),
      );
      setQuotes((current) => current.map((item) => item.id === result.id ? result : item));
      setSavedQuote(result);
      setAccepting(null);
      setAcceptanceReference("");
      setAcceptanceNote("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to accept and award the quote.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="space-y-6">
      <div className="rounded-xl border border-brand-gold/30 bg-iron-950 p-6 text-white shadow-brand">
        <div className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-gold">Quote to job</div>
        <h1 className="mt-2 text-3xl font-semibold">Customer Quotes</h1>
        <p className="mt-2 max-w-3xl text-sm text-iron-200">Capture verbal information once. Drafts stay non-binding; management acceptance creates the awarded IHOS job and permanent job number.</p>
      </div>

      {error ? <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
      {savedQuote ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
          <span>{savedQuote.status === "accepted" ? `${savedQuote.quote_number} accepted — job ${savedQuote.job_number} created.` : `${savedQuote.quote_number} saved in IHOS as ${savedQuote.status}.`}</span>
          <Link to={`/projects/${savedQuote.project_id}`} className="inline-flex items-center gap-2 font-semibold">Open Project Workspace <ArrowRight className="h-4 w-4" /></Link>
        </div>
      ) : null}

      {!editing ? <DraftSaveIndicator status={draft.status} lastSavedAt={draft.lastSavedAt} /> : null}

      <form onSubmit={submit} className="space-y-5 rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><h2 className="text-xl font-semibold text-iron-950">{editing ? `Edit ${editing.quote_number}` : "New verbal quote intake"}</h2><p className="mt-1 text-sm text-iron-500">Required information is saved in IHOS; nothing is sent or accepted by this form.</p></div>
          {editing ? <button type="button" onClick={reset} className="rounded-md border border-iron-200 px-3 py-2 text-sm font-semibold">Cancel edit</button> : null}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Project / work name" value={projectName} onChange={setProjectName} required />
          <Field label="Customer / company" value={customerName} onChange={setCustomerName} required />
          <Field label="Customer email" type="email" value={customerEmail} onChange={setCustomerEmail} />
          <Field label="Customer phone" value={customerPhone} onChange={setCustomerPhone} />
          <div className="md:col-span-2"><Field label="Site address" value={siteAddress} onChange={setSiteAddress} /></div>
          <label className="grid gap-1 text-sm font-medium text-iron-700 md:col-span-2">Scope summary<textarea required value={scopeSummary} onChange={(event) => setScopeSummary(event.target.value)} className="min-h-28 rounded-md border border-iron-200 px-3 py-2" /></label>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between"><h3 className="font-semibold text-iron-950">Quote line items</h3><button type="button" onClick={() => setLineItems((current) => [...current, blankLine()])} className="inline-flex items-center gap-2 rounded-md border border-iron-200 px-3 py-2 text-sm font-semibold"><Plus className="h-4 w-4" /> Add line</button></div>
          {lineItems.map((line, index) => (
            <div key={index} className="grid gap-3 rounded-md border border-iron-100 p-3 md:grid-cols-[1fr_100px_100px_140px_44px]">
              <Field label={`Item ${index + 1}`} value={line.description} onChange={(value) => setLine(index, { description: value })} required />
              <Field label={`Quantity ${index + 1}`} type="number" value={line.quantity} onChange={(value) => setLine(index, { quantity: value })} required />
              <Field label={`Unit ${index + 1}`} value={line.unit} onChange={(value) => setLine(index, { unit: value })} required />
              <Field label={`Unit price ${index + 1}`} type="number" value={line.unit_price} onChange={(value) => setLine(index, { unit_price: value })} required />
              <button type="button" aria-label={`Remove item ${index + 1}`} disabled={lineItems.length === 1} onClick={() => setLineItems((current) => current.filter((_, itemIndex) => itemIndex !== index))} className="mt-6 grid h-10 place-items-center rounded-md border border-iron-200 text-red-700 disabled:opacity-30"><Trash2 className="h-4 w-4" /></button>
            </div>
          ))}
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <label className="grid gap-1 text-sm font-medium text-iron-700">Assumptions, one per line<textarea value={assumptions} onChange={(event) => setAssumptions(event.target.value)} className="min-h-24 rounded-md border border-iron-200 px-3 py-2" /></label>
          <label className="grid gap-1 text-sm font-medium text-iron-700">Exclusions, one per line<textarea value={exclusions} onChange={(event) => setExclusions(event.target.value)} className="min-h-24 rounded-md border border-iron-200 px-3 py-2" /></label>
          <Field label="GST rate %" type="number" value={gstRate} onChange={setGstRate} required />
          <Field label="Quote date" type="date" value={quoteDate} onChange={setQuoteDate} required />
          <Field label="Valid until" type="date" value={validUntil} onChange={setValidUntil} />
          <Field label="Internal / customer notes" value={notes} onChange={setNotes} />
        </div>
        <div className="grid gap-3 rounded-md bg-iron-50 p-4 text-sm sm:grid-cols-3"><Total label="Subtotal" value={totals.subtotal} /><Total label="GST" value={totals.gst} /><Total label="Quote total" value={totals.total} strong /></div>
        <button disabled={saving || !projectName.trim() || !customerName.trim() || !scopeSummary.trim() || lineItems.some((line) => !line.description.trim() || Number(line.quantity) <= 0)} className="rounded-md bg-brand-gold px-4 py-2 font-semibold text-brand-black disabled:opacity-50">{saving ? "Saving…" : editing ? "Save quote revision" : "Save draft quote in IHOS"}</button>
      </form>

      {accepting ? (
        <section className="rounded-xl border-2 border-brand-gold bg-white p-5 shadow-brand" aria-labelledby="accept-quote-title">
          <h2 id="accept-quote-title" className="text-xl font-semibold text-iron-950">Accept {accepting.quote_number} and create the awarded job</h2>
          <p className="mt-2 text-sm text-iron-600">This is the controlled commitment step. IHOS will award {accepting.project_name}, allocate its permanent job number, and create its Project Workspace.</p>
          <div className="mt-4 grid gap-4 md:grid-cols-2"><Field label="Acceptance reference" value={acceptanceReference} onChange={setAcceptanceReference} required /><Field label="Acceptance note" value={acceptanceNote} onChange={setAcceptanceNote} /></div>
          <div className="mt-4 flex gap-2"><button type="button" disabled={saving || !acceptanceReference.trim()} onClick={() => void accept()} className="inline-flex items-center gap-2 rounded-md bg-brand-gold px-4 py-2 font-semibold text-brand-black disabled:opacity-50"><CheckCircle2 className="h-4 w-4" /> Confirm acceptance and create job</button><button type="button" onClick={() => setAccepting(null)} className="rounded-md border border-iron-200 px-4 py-2 font-semibold">Cancel</button></div>
        </section>
      ) : null}

      <section className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
        <h2 className="text-xl font-semibold text-iron-950">Customer quote register</h2>
        <p className="mt-1 text-sm text-iron-500">Draft and sent quotes have no job number. Only management acceptance creates an awarded job.</p>
        <div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-iron-50 text-xs uppercase tracking-wide text-iron-500"><tr><th className="px-3 py-2">Quote</th><th className="px-3 py-2">Customer / project</th><th className="px-3 py-2">Total</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Job</th><th className="px-3 py-2">Actions</th></tr></thead><tbody>
          {quotes.map((quote) => <tr key={quote.id} className="border-t border-iron-100"><td className="px-3 py-3 font-semibold text-iron-950">{quote.quote_number}</td><td className="px-3 py-3"><div>{quote.customer_name}</div><div className="text-xs text-iron-500">{quote.project_name}</div></td><td className="px-3 py-3">{money.format(Number(quote.total))}</td><td className="px-3 py-3 capitalize">{quote.status}</td><td className="px-3 py-3">{quote.job_number ?? "Not awarded"}</td><td className="px-3 py-3"><div className="flex flex-wrap gap-2">{quote.status !== "accepted" && quote.status !== "declined" && quote.status !== "expired" ? <><button type="button" onClick={() => edit(quote)} className="font-semibold text-iron-700">Edit</button>{quote.status === "draft" ? <button type="button" onClick={() => void markSent(quote)} className="font-semibold text-iron-700">Mark sent</button> : null}{user?.role === "admin" || user?.role === "operations_manager" ? <button type="button" onClick={() => { setAccepting(quote); setAcceptanceReference(""); setAcceptanceNote(""); }} className="font-semibold text-emerald-700">Accept / award</button> : null}</> : null}<a href={customerQuotesApi.pdfUrl(quote.id)} target="_blank" rel="noopener noreferrer" className="font-semibold text-iron-700">Open PDF</a><Link to={`/projects/${quote.project_id}`} className="font-semibold text-iron-700">Project</Link></div></td></tr>)}
          {!quotes.length ? <tr><td colSpan={6} className="px-3 py-8 text-center text-iron-500">No customer quotes yet.</td></tr> : null}
        </tbody></table></div>
      </section>
    </section>
  );

  function setLine(index: number, patch: Partial<CustomerQuoteLineItem>) {
    setLineItems((current) => current.map((line, lineIndex) => lineIndex === index ? { ...line, ...patch } : line));
  }
}

function Field({ label, value, onChange, type = "text", required = false }: { label: string; value: string; onChange: (value: string) => void; type?: string; required?: boolean }) {
  return <label className="grid gap-1 text-sm font-medium text-iron-700">{label}<input required={required} type={type} step={type === "number" ? "0.01" : undefined} min={type === "number" ? "0" : undefined} value={value} onChange={(event) => onChange(event.target.value)} className="rounded-md border border-iron-200 px-3 py-2" /></label>;
}

function Total({ label, value, strong = false }: { label: string; value: number; strong?: boolean }) {
  return <div><div className="text-iron-500">{label}</div><div className={strong ? "text-lg font-semibold text-iron-950" : "font-semibold text-iron-800"}>{money.format(value)}</div></div>;
}

function lines(value: string) {
  return value.split("\n").map((item) => item.trim()).filter(Boolean);
}

function text(value: unknown) {
  return typeof value === "string" ? value : "";
}
