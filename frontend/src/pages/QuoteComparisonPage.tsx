import { Plus, Trash2 } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";

import { QuoteComparisonResponse, quotesApi, SupplierQuoteCreate } from "../api/quotes";
import { ProjectScopeNotice } from "../components/ProjectScopeNotice";
import { readProjectContext } from "../utils/projectContext";

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
    is_selected: false,
    selection_reason: "",
    exclusions: [],
    notes: "",
  };
}

export function QuoteComparisonPage() {
  const location = useLocation();
  const projectContext = readProjectContext(location.search);
  const [quotes, setQuotes] = useState<SupplierQuoteCreate[]>([blankQuote(), blankQuote()]);
  const [result, setResult] = useState<QuoteComparisonResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validQuoteCount = useMemo(
    () => quotes.filter((quote) => quote.supplier_name && quote.scope && quote.amount >= 0).length,
    [quotes],
  );

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
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
          selection_reason: quote.selection_reason?.trim() || null,
          notes: quote.notes?.trim() || null,
        }));
      setResult(await quotesApi.compare(cleanQuotes));
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

  return (
    <section className="space-y-6">
      <div className="border-b border-iron-100 pb-6">
        <h1 className="text-3xl font-semibold text-iron-950">Quote Comparison</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
          Manual supplier quote comparison for MVP. Enter quotes by line item and scope, mark the selected supplier if needed, and review the delta from lowest price.
        </p>
      </div>

      <ProjectScopeNotice name={projectContext.projectName} />

      <form className="space-y-4" onSubmit={submit}>
        <div className="flex items-center justify-between gap-3">
          <div className="text-sm text-iron-500">Valid quotes ready: {validQuoteCount}</div>
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
                <Input label="Amount" type="number" value={String(quote.amount)} onChange={(value) => updateQuote(index, { amount: Number(value) })} />
                <Input label="Selection Reason" value={quote.selection_reason ?? ""} onChange={(value) => updateQuote(index, { selection_reason: value })} />
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
          {isLoading ? "Comparing..." : "Compare quotes"}
        </button>
      </form>

      {result ? (
        <div className="space-y-4 rounded-md border border-iron-100 bg-white p-5">
          <h2 className="text-lg font-semibold text-iron-950">Comparison Summary</h2>
          <div className="grid gap-3 md:grid-cols-3">
            <SummaryCard label="Lowest Total" value={moneyFormatter.format(result.total_lowest)} />
            <SummaryCard label="Selected Total" value={moneyFormatter.format(result.total_selected)} />
            <SummaryCard label="Delta" value={moneyFormatter.format(result.delta_from_lowest)} />
          </div>

          <div className="overflow-hidden rounded-md border border-iron-100">
            <table className="w-full text-left text-sm">
              <thead className="bg-iron-50 text-xs uppercase tracking-wide text-iron-500">
                <tr>
                  <th className="px-3 py-2">Line Item</th>
                  <th className="px-3 py-2">Scope</th>
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
                    <td className="px-3 py-2 text-iron-600">{line.lowest_supplier} - {moneyFormatter.format(line.lowest_amount ?? 0)}</td>
                    <td className="px-3 py-2 text-iron-600">
                      {line.selected_supplier} - {moneyFormatter.format(line.selected_amount ?? 0)}
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
