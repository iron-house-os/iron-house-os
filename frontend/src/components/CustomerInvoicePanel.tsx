import { Download, Plus } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { CustomerInvoice, financeApi } from "../api/finance";

const money = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" });
const today = () => new Date().toISOString().slice(0, 10);

export function CustomerInvoicePanel() {
  const [items, setItems] = useState<CustomerInvoice[]>([]);
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [customer, setCustomer] = useState("");
  const [address, setAddress] = useState("");
  const [project, setProject] = useState("");
  const [site, setSite] = useState("");
  const [invoiceDate, setInvoiceDate] = useState(today());
  const [dueDate, setDueDate] = useState(today());
  const [description, setDescription] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [unitPrice, setUnitPrice] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function refresh() { try { setItems((await financeApi.getCustomerInvoices()).items); } catch (current) { setError(current instanceof Error ? current.message : "Unable to load customer invoices."); } }
  useEffect(() => { void refresh(); }, []);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(null);
    try {
      await financeApi.createCustomerInvoice({ invoice_number: invoiceNumber, customer_name: customer, customer_address: address, project_name: project, site_address: site || null, invoice_date: invoiceDate, due_date: dueDate, terms: "Net 30", gst_rate: "5", line_items: [{ description, quantity, unit_price: unitPrice }] });
      setInvoiceNumber(""); setCustomer(""); setAddress(""); setProject(""); setSite(""); setDescription(""); setQuantity("1"); setUnitPrice(""); await refresh();
    } catch (current) { setError(current instanceof Error ? current.message : "Unable to create customer invoice."); }
  }
  async function transition(invoice: CustomerInvoice, status: CustomerInvoice["status"]) { try { await financeApi.updateCustomerInvoiceStatus(invoice.id, status); await refresh(); } catch (current) { setError(current instanceof Error ? current.message : "Unable to update invoice."); } }

  return <section className="rounded-md border border-iron-100 bg-white p-5">
    <div className="flex items-center gap-2"><Plus className="h-4 w-4" /><h2 className="font-semibold">Customer billing</h2></div>
    <p className="mt-1 text-sm text-iron-500">Server-calculated CAD invoices. Approval is required before issue; development records are clearly identified.</p>
    {error ? <div role="alert" className="mt-3 text-sm text-red-700">{error}</div> : null}
    <form onSubmit={submit} className="mt-4 grid gap-3 border-t border-iron-100 pt-4 md:grid-cols-2 xl:grid-cols-4">
      <Field label="Invoice number" value={invoiceNumber} onChange={setInvoiceNumber} /><Field label="Customer" value={customer} onChange={setCustomer} /><Field label="Customer address" value={address} onChange={setAddress} /><Field label="Project" value={project} onChange={setProject} /><Field label="Job-site address" value={site} onChange={setSite} /><Field label="Invoice date" value={invoiceDate} onChange={setInvoiceDate} type="date" /><Field label="Due date" value={dueDate} onChange={setDueDate} type="date" /><Field label="Description" value={description} onChange={setDescription} /><Field label="Quantity" value={quantity} onChange={setQuantity} type="number" /><Field label="Unit price" value={unitPrice} onChange={setUnitPrice} type="number" />
      <button disabled={!invoiceNumber || !customer || !address || !project || !description || !unitPrice} className="self-end rounded-md bg-brand-gold px-4 py-2 text-sm font-semibold text-brand-black disabled:opacity-50">Create draft invoice</button>
    </form>
    <div className="mt-5 overflow-x-auto" tabIndex={0} role="region" aria-label="Customer invoice register">
      <table className="w-full min-w-[820px] text-left text-sm"><thead className="bg-iron-50 text-xs uppercase text-iron-500"><tr><th className="px-4 py-3">Invoice</th><th>Customer</th><th>Project / site</th><th>Total</th><th>Status</th><th>Controls</th></tr></thead><tbody>{items.map((invoice) => <tr key={invoice.id} className="border-t border-iron-100"><td className="px-4 py-3 font-semibold">{invoice.invoice_number}{invoice.development_seed_key ? <span className="ml-2 rounded bg-amber-100 px-2 py-1 text-xs">Development only</span> : null}</td><td>{invoice.customer_name}</td><td>{invoice.project_name}<div className="text-xs text-iron-500">{invoice.site_address || "Job-site address not provided"}</div></td><td>{money.format(Number(invoice.total))}</td><td>{invoice.status}</td><td><div className="flex gap-2">{invoice.status === "draft" ? <button onClick={() => void transition(invoice, "approved")} className="font-semibold underline">Approve</button> : null}{invoice.status === "approved" ? <button onClick={() => void transition(invoice, "issued")} className="font-semibold underline">Issue</button> : null}<a href={financeApi.customerInvoicePdfUrl(invoice.id)} className="inline-flex items-center gap-1 font-semibold underline"><Download className="h-3 w-3" />PDF</a></div></td></tr>)}</tbody></table>
    </div>
  </section>;
}

function Field({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (value: string) => void; type?: string }) { return <label className="text-sm font-semibold">{label}<input aria-label={label} type={type} step={type === "number" ? "0.01" : undefined} value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-md border border-iron-100 px-3 py-2 font-normal" /></label>; }
