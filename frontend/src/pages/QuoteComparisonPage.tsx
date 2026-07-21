import { ArrowRight, Plus, Trash2 } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import {
  QuoteComparisonResponse,
  QuoteEstimateSelectionResponse,
  quotesApi,
  SupplierQuoteCreate,
} from "../api/quotes";
import { ProjectScopeNotice } from "../components/ProjectScopeNotice";
import { readEffectiveProjectContext } from "../utils/projectContext";

const moneyFormatter = new Intl.NumberFormat("en-CA", {
  style: "currency",
  currency: "CAD",
  maximumFractionDigits: 2,
});

function blankQuote(): SupplierQuoteCreate {
  return {
    supplier_name: "",
    line_item_code: "",
    line_item_description: "",
    scope: "",
    scope_type: "material",
    status: "received",
    amount: 0,
    is_qualified: true,
    qualification_notes: [],
    is_selected: false,
    selection_reason: "",
    exclusions: [],
    notes: "",
  };
}

export function QuoteComparisonPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const projectContext = readEffectiveProjectContext(location.search);
  const [quotes, setQuotes] = useState<SupplierQuoteCreate[]>([blankQuote(), blankQuote()]);
  const [result, setResult] = useState<QuoteComparisonResponse | null>(null);
  const [selection, setSelection] = useState<QuoteEstimateSelectionResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validQuoteCount = useMemo(
    () => quotes.filter((quote) => quote.supplier_name && quote.scope && quote.amount > 0).length,
    [quotes],
  );

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setResult(null);
    setSelection(null);
    try {
      const cleanQuotes = quotes
        .filter((quote) => quote.supplier_name.trim() && quote.scope.trim())
        .map((quote) => ({
          ...quote,
          supplier_name: quote.supplier_name.trim(),
          line_item_code: quote.line_item_code?.trim() || null,
          line_item_description: quote.line_item_description?.trim() || quote.scope.trim(),
          scope: quote.scope.trim(),
          amount: Number(quote.amount) || 0,
          qualification_notes: quote.qualification_notes.map((note) => note.trim()).filter(Boolean),
          selection_reason: quote.selection_reason?.trim() || null,
          notes: quote.notes?.trim() || null,
        }));
      const [comparisonResult, selectionResult] = await Promise.all([
        quotesApi.compare(cleanQuotes),
        quotesApi.estimateSelection(cleanQuotes),
      ]);
      setResult(comparisonResult);
      setSelection(selectionResult);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to compare quotes");
    } finally {
      setIsLoading(false);
    }
  }

  function updateQuote(index: number, patch: Partial<SupplierQuoteCreate>) {
    setQuotes((current) => current.map((quote, quoteIndex) => (quoteIndex === index ? { ...quote, ...patch } : quote)));
  }

  function removeQuote(index: number) {
    setQuotes((current) => current.filter((_, quoteIndex) => quoteIndex !== index));
  }

  function useSelectedQuotes() {
    if (!selection?.ready_for_estimate) return;
    navigate(
      { pathname: "/estimating", search: location.search },
      { state: { quoteLineItems: selection.line_items } },
    );
  }

  return (
    <section className="space-y-6">
      <div className="border-b border-iron-100 pb-6">
        <h1 className="text-3xl font-semibold text-iron-950">Quote Comparison</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
          Qualify supplier quotes by estimate line, compare received pricing, and document any non-low selection before sending it to Estimating.
        </p>
      </div>

      <ProjectScopeNotice name={projectContext.projectName} />

      <form className="space-y-4" onSubmit={submit}>
        <div className="flex items-center justify-between gap-3">
          <div className="text-sm text-iron-500">Complete positive quotes: {validQuoteCount}</div>
          <button
            type="button"
            onClick={() => setQuotes((current) => [...current, blankQuote()])}
            className="inline-flex items-center gap-2 rounded-md border border-iron-100 bg-white px-3 py-2 text-sm font-medium text-iron-800"
          >
            <Plus className="h-4 w-4" />
            Add quote
          </button>
        </div>

        <div className="space-y-3">
          {quotes.map((quote, index) => (
            <div key={index} className="rounded-md border border-iron-100 bg-white p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <h2 className="text-sm font-semibold text-iron-950">Quote {index + 1}</h2>
                <button type="button" onClick={() => removeQuote(index)} className="inline-flex items-center gap-2 text-sm text-red-600" disabled={quotes.length <= 1}>
                  <Trash2 className="h-4 w-4" />
                  Remove
                </button>
              </div>

              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <Input label="Supplier" value={quote.supplier_name} onChange={(value) => updateQuote(index, { supplier_name: value })} />
                <Input label="Line Item Code" value={quote.line_item_code ?? ""} onChange={(value) => updateQuote(index, { line_item_code: value })} />
                <Input label="Line Item" value={quote.line_item_description ?? ""} onChange={(value) => updateQuote(index, { line_item_description: value })} />
                <Input label="Scope" value={quote.scope} onChange={(value) => updateQuote(index, { scope: value })} />
                <label className="grid gap-1 text-sm">
                  <span className="font-medium text-iron-700">Scope Type</span>
                  <select value={quote.scope_type} onChange={(event) => updateQuote(index, { scope_type: event.target.value as SupplierQuoteCreate["scope_type"] })} className="rounded-md border border-iron-100 px-3 py-2">
                    <option value="material">Material</option>
                    <option value="subcontract">Subcontract</option>
                    <option value="trucking">Trucking</option>
                    <option value="disposal">Disposal</option>
                    <option value="equipment">Equipment</option>
                    <option value="other">Other</option>
                  </select>
                </label>
                <label className="grid gap-1 text-sm">
                  <span className="font-medium text-iron-700">Status</span>
                  <select value={quote.status} onChange={(event) => updateQuote(index, { status: event.target.value as SupplierQuoteCreate["status"] })} className="rounded-md border border-iron-100 px-3 py-2">
                    <option value="received">Received</option>
                    <option value="requested">Requested</option>
                    <option value="declined">Declined</option>
                    <option value="bounced">Bounced</option>
                    <option value="rejected">Rejected</option>
                  </select>
                </label>
                <Input label="Amount" type="number" value={String(quote.amount)} onChange={(value) => updateQuote(index, { amount: Number(value) })} />
                <Input label="Selection Reason" value={quote.selection_reason ?? ""} onChange={(value) => updateQuote(index, { selection_reason: value })} />
                <Input
                  label="Qualification Notes"
                  value={quote.qualification_notes.join("; ")}
                  onChange={(value) => updateQuote(index, { qualification_notes: value ? [value] : [] })}
                />
                <Input label="Quote Notes" value={quote.notes ?? ""} onChange={(value) => updateQuote(index, { notes: value })} />
                <label className="flex items-end gap-2 pb-2 text-sm font-medium text-iron-700">
                  <input type="checkbox" checked={quote.is_qualified} onChange={(event) => updateQuote(index, { is_qualified: event.target.checked })} className="h-4 w-4" />
                  Qualified quote
                </label>
                <label className="flex items-end gap-2 pb-2 text-sm font-medium text-iron-700">
                  <input type="checkbox" checked={quote.is_selected} onChange={(event) => updateQuote(index, { is_selected: event.target.checked })} className="h-4 w-4" />
                  Selected quote
                </label>
              </div>
            </div>
          ))}
        </div>

        {error ? <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}

        <button type="submit" className="rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white" disabled={isLoading}>
          {isLoading ? "Comparing..." : "Compare and qualify quotes"}
        </button>
      </form>

      {result && selection ? (
        <div className="space-y-4 rounded-md border border-iron-100 bg-white p-5">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <h2 className="text-lg font-semibold text-iron-950">Comparison Summary</h2>
            <button
              type="button"
              onClick={useSelectedQuotes}
              disabled={!selection.ready_for_estimate}
              className="inline-flex items-center justify-center gap-2 rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-iron-300"
            >
              Use selected quotes in estimate
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>

          {selection.ready_for_estimate ? (
            <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
              Ready for estimate: every line has one qualified supplier selection.
            </div>
          ) : (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              <div className="font-semibold">Resolve before estimate handoff</div>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {selection.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}
              </ul>
            </div>
          )}

          <div className="grid gap-3 md:grid-cols-3">
            <SummaryCard label="Lowest Qualified Total" value={moneyFormatter.format(result.total_lowest)} />
            <SummaryCard label="Selected Total" value={moneyFormatter.format(result.total_selected)} />
            <SummaryCard label="Delta" value={moneyFormatter.format(result.delta_from_lowest)} />
          </div>

          <div className="overflow-hidden rounded-md border border-iron-100">
            <table className="w-full text-left text-sm">
              <thead className="bg-iron-50 text-xs uppercase tracking-wide text-iron-500">
                <tr>
                  <th className="px-3 py-2">Line Item</th>
                  <th className="px-3 py-2">Scope</th>
                  <th className="px-3 py-2">Qualified</th>
                  <th className="px-3 py-2">Lowest</th>
                  <th className="px-3 py-2">Selected</th>
                  <th className="px-3 py-2">Reason</th>
                </tr>
              </thead>
              <tbody>
                {result.lines.map((line, index) => (
                  <tr key={`${line.line_item_code ?? "line"}-${line.scope}-${index}`} className="border-t border-iron-100">
                    <td className="px-3 py-2 font-medium text-iron-950">{line.line_item_description}</td>
                    <td className="px-3 py-2 text-iron-600">{line.scope}</td>
                    <td className="px-3 py-2 text-iron-600">{line.qualified_quote_count} / {line.quote_count}</td>
                    <td className="px-3 py-2 text-iron-600">{line.lowest_supplier ? `${line.lowest_supplier} - ${moneyFormatter.format(line.lowest_amount ?? 0)}` : "—"}</td>
                    <td className="px-3 py-2 text-iron-600">
                      {line.selected_supplier ? `${line.selected_supplier} - ${moneyFormatter.format(line.selected_amount ?? 0)}` : "—"}
                      {!line.selected_is_lowest ? <span className="ml-2 rounded bg-amber-100 px-2 py-1 text-xs text-amber-700">Not lowest</span> : null}
                    </td>
                    <td className="px-3 py-2 text-iron-600">{line.selection_reason ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function Input({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return <label className="grid gap-1 text-sm"><span className="font-medium text-iron-700">{label}</span><input type={type} value={value} onChange={(event) => onChange(event.target.value)} className="rounded-md border border-iron-100 px-3 py-2" /></label>;
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md border border-iron-100 p-4"><div className="text-sm font-medium text-iron-500">{label}</div><div className="mt-2 text-2xl font-semibold text-iron-950">{value}</div></div>;
}
