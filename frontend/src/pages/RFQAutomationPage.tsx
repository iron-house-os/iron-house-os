import { FileStack, Plus, RefreshCw, Trash2 } from "lucide-react";
import { FormEvent, useState } from "react";
import { useLocation } from "react-router-dom";

import {
  RFQAutomationInputItem,
  RFQAutomationResponse,
  SourceSignal,
  rfqAutomationApi,
} from "../api/rfqAutomation";
import { ProjectScopeNotice } from "../components/ProjectScopeNotice";
import { readProjectContext } from "../utils/projectContext";

const signals: SourceSignal[] = ["quantity", "municipality", "estimate", "manual"];

function blankItem(): RFQAutomationInputItem {
  return {
    category: "pipe",
    description: "PVC storm pipe",
    quantity: 100,
    unit: "m",
    source: "quantity",
  };
}

export function RFQAutomationPage() {
  const location = useLocation();
  const projectContext = readProjectContext(location.search);
  const [projectName, setProjectName] = useState(projectContext.projectName ?? "Iron House Tender Review");
  const [municipality, setMunicipality] = useState("Surrey");
  const [includeDefaults, setIncludeDefaults] = useState(true);
  const [items, setItems] = useState<RFQAutomationInputItem[]>([
    blankItem(),
    { category: "structures", description: "Type 1 manholes", quantity: 2, unit: "EA", source: "quantity" },
    { category: "traffic", description: "Traffic control required by municipality", source: "municipality" },
  ]);
  const [result, setResult] = useState<RFQAutomationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function recommend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      setResult(
        await rfqAutomationApi.recommend({
          project_name: projectName,
          municipality,
          include_default_civil_scopes: includeDefaults,
          items: items.filter((item) => item.description.trim()),
        }),
      );
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to recommend RFQ scopes");
    } finally {
      setIsLoading(false);
    }
  }

  function updateItem(index: number, patch: Partial<RFQAutomationInputItem>) {
    setItems((current) => current.map((item, currentIndex) => (currentIndex === index ? { ...item, ...patch } : item)));
  }

  function removeItem(index: number) {
    setItems((current) => current.filter((_, currentIndex) => currentIndex !== index));
  }

  return (
    <section className="space-y-6">
      <div className="border-b border-iron-100 pb-6">
        <h1 className="text-3xl font-semibold text-iron-950">RFQ Automation</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
          Build 27 review-only RFQ planner. Converts quantity, municipality, estimate, and manual signals into procurement scope recommendations.
        </p>
      </div>

      <ProjectScopeNotice name={projectContext.projectName} />

      <form className="space-y-6" onSubmit={recommend}>
        <div className="rounded-md border border-iron-100 bg-white p-5">
          <h2 className="text-base font-semibold text-iron-950">Project setup</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <Input label="Project name" value={projectName} onChange={setProjectName} />
            <Input label="Municipality" value={municipality} onChange={setMunicipality} />
            <label className="flex items-end gap-2 pb-2 text-sm font-medium text-iron-700">
              <input type="checkbox" checked={includeDefaults} onChange={(event) => setIncludeDefaults(event.target.checked)} />
              Include default civil RFQ scopes
            </label>
          </div>
        </div>

        <div className="rounded-md border border-iron-100 bg-white p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-iron-950">Source signals</h2>
              <p className="mt-1 text-sm text-iron-500">Use takeoff items, municipal requirements, estimate scopes, or manual notes to create RFQ packages.</p>
            </div>
            <button type="button" onClick={() => setItems((current) => [...current, blankItem()])} className="inline-flex items-center gap-2 rounded-md border border-iron-100 px-3 py-2 text-sm font-semibold text-iron-800">
              <Plus className="h-4 w-4" /> Add signal
            </button>
          </div>

          <div className="mt-4 space-y-4">
            {items.map((item, index) => (
              <div key={index} className="rounded-md border border-iron-100 p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div className="text-sm font-semibold text-iron-950">Signal {index + 1}</div>
                  <button type="button" onClick={() => removeItem(index)} disabled={items.length <= 1} className="inline-flex items-center gap-2 text-sm text-red-700">
                    <Trash2 className="h-4 w-4" /> Remove
                  </button>
                </div>
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
                  <Input label="Category" value={item.category} onChange={(value) => updateItem(index, { category: value })} />
                  <Input label="Description" value={item.description} onChange={(value) => updateItem(index, { description: value })} />
                  <Input label="Quantity" type="number" value={String(item.quantity ?? "")} onChange={(value) => updateItem(index, { quantity: value === "" ? null : Number(value) })} />
                  <Input label="Unit" value={item.unit ?? ""} onChange={(value) => updateItem(index, { unit: value })} />
                  <label className="grid gap-1 text-sm">
                    <span className="font-medium text-iron-700">Source</span>
                    <select value={item.source} onChange={(event) => updateItem(index, { source: event.target.value as SourceSignal })} className="rounded-md border border-iron-100 px-3 py-2">
                      {signals.map((signal) => <option key={signal} value={signal}>{signal}</option>)}
                    </select>
                  </label>
                </div>
              </div>
            ))}
          </div>
        </div>

        {error ? <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}

        <button type="submit" disabled={isLoading} className="inline-flex items-center gap-2 rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white">
          {isLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <FileStack className="h-4 w-4" />}
          Recommend RFQ scopes
        </button>
      </form>

      {result ? <RFQAutomationResult result={result} /> : null}
    </section>
  );
}

function RFQAutomationResult({ result }: { result: RFQAutomationResponse }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <SummaryCard label="Recommendations" value={String(result.recommendation_count)} />
        <SummaryCard label="High Priority" value={String(result.high_priority_count)} />
        <SummaryCard label="Municipality" value={result.municipality ?? "Not set"} />
      </div>

      {result.warnings.length ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <div className="font-semibold">Review warnings</div>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {result.warnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        </div>
      ) : null}

      <div className="space-y-4">
        {result.recommendations.map((recommendation) => (
          <div key={recommendation.scope} className="rounded-md border border-iron-100 bg-white p-5">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <div className="text-xs uppercase tracking-wide text-iron-500">Priority {recommendation.priority} · {recommendation.scope}</div>
                <h3 className="mt-1 text-base font-semibold text-iron-950">{recommendation.title}</h3>
                <p className="mt-2 text-sm leading-6 text-iron-500">{recommendation.reason}</p>
              </div>
              <span className="rounded-full bg-iron-950 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-white">review only</span>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <Note title="Supplier categories" text={recommendation.supplier_categories.join(", ")} />
              <Note title="Required documents" text={recommendation.required_documents.join(", ")} />
              <Note title="Source signals" text={recommendation.source_signals.join(", ")} />
            </div>
            {recommendation.review_notes.length ? (
              <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-iron-600">
                {recommendation.review_notes.map((note) => <li key={note}>{note}</li>)}
              </ul>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function Input({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return (
    <label className="grid gap-1 text-sm">
      <span className="font-medium text-iron-700">{label}</span>
      <input type={type} value={value} onChange={(event) => onChange(event.target.value)} className="rounded-md border border-iron-100 px-3 py-2" />
    </label>
  );
}

function Note({ title, text }: { title: string; text: string }) {
  return <div className="rounded-md bg-iron-50 p-3"><div className="text-xs font-semibold uppercase tracking-wide text-iron-500">{title}</div><p className="mt-1 text-sm leading-6 text-iron-700">{text}</p></div>;
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md border border-iron-100 bg-white p-4"><div className="text-sm font-medium text-iron-500">{label}</div><div className="mt-2 text-xl font-semibold text-iron-950">{value}</div></div>;
}
