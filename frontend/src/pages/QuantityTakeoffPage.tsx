import { Calculator, Plus, RefreshCw, Trash2 } from "lucide-react";
import { FormEvent, useState } from "react";
import { useLocation } from "react-router-dom";

import {
  QuantityCategory,
  QuantityItem,
  QuantityRegisterResponse,
  QuantitySource,
  QuantityUnit,
  takeoffApi,
} from "../api/takeoff";
import { ProjectScopeNotice } from "../components/ProjectScopeNotice";
import { TakeoffEnginePanel } from "../components/TakeoffEnginePanel";
import { TakeoffSavePanel } from "../components/TakeoffSavePanel";
import { readEffectiveProjectContext } from "../utils/projectContext";

const categories: QuantityCategory[] = ["pipe", "structures", "asphalt", "concrete", "earthworks", "landscape", "traffic", "misc"];
const units: QuantityUnit[] = ["LS", "EA", "m", "m2", "m3", "t", "hr", "day"];
const sources: QuantitySource[] = ["manual", "drawing_intelligence", "ocr", "import", "estimate_override", "takeoff_engine"];

function blankItem(): QuantityItem {
  return {
    code: "Q-001",
    description: "PVC storm pipe",
    category: "pipe",
    quantity: 100,
    unit: "m",
    source: "manual",
    confidence: 1,
    estimate_ready: true,
    drawing_reference: "C-101",
    notes: "Manual MVP entry",
  };
}

export function QuantityTakeoffPage() {
  const location = useLocation();
  const projectContext = readEffectiveProjectContext(location.search);
  const [projectName, setProjectName] = useState(projectContext.projectName ?? "Iron House Tender Review");
  const [items, setItems] = useState<QuantityItem[]>([
    blankItem(),
    {
      code: "Q-002",
      description: "Type 1 manhole",
      category: "structures",
      quantity: 2,
      unit: "EA",
      source: "manual",
      confidence: 1,
      estimate_ready: true,
      drawing_reference: "C-101",
      notes: "Manual structure count",
    },
  ]);
  const [summary, setSummary] = useState<QuantityRegisterResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function summarize(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      setSummary(
        await takeoffApi.summarize({
          project_name: projectName,
          project_id: projectContext.projectId,
          items: items.filter((item) => item.description.trim()),
        }),
      );
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to summarize quantities");
    } finally {
      setIsLoading(false);
    }
  }

  function updateItem(index: number, patch: Partial<QuantityItem>) {
    setItems((current) => current.map((item, currentIndex) => (currentIndex === index ? { ...item, ...patch } : item)));
  }

  function removeItem(index: number) {
    setItems((current) => current.filter((_, currentIndex) => currentIndex !== index));
  }

  const activeItems = items.filter((item) => item.description.trim());

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-iron-100 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-iron-950">Quantity Takeoff Engine</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
            Build 62 quantity register with project save support, generated BOQ items, readiness checks, conflicts, and estimating handoff.
          </p>
        </div>
      </div>

      <ProjectScopeNotice name={projectContext.projectName} />
      <TakeoffEnginePanel projectName={projectName} projectId={projectContext.projectId} manualItems={activeItems} />
      <TakeoffSavePanel projectId={projectContext.projectId} items={activeItems} quantityRegister={summary} />

      <form className="space-y-6" onSubmit={summarize}>
        <div className="rounded-md border border-iron-100 bg-white p-5">
          <h2 className="text-base font-semibold text-iron-950">Project</h2>
          <label className="mt-4 grid gap-1 text-sm">
            <span className="font-medium text-iron-700">Project name</span>
            <input value={projectName} onChange={(event) => setProjectName(event.target.value)} className="rounded-md border border-iron-100 px-3 py-2" />
          </label>
        </div>

        <div className="rounded-md border border-iron-100 bg-white p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-iron-950">Manual Quantity Register</h2>
              <p className="mt-1 text-sm text-iron-500">Track quantities by category, unit, source, confidence, and estimate readiness.</p>
            </div>
            <button type="button" onClick={() => setItems((current) => [...current, blankItem()])} className="inline-flex items-center gap-2 rounded-md border border-iron-100 px-3 py-2 text-sm font-semibold text-iron-800">
              <Plus className="h-4 w-4" /> Add quantity
            </button>
          </div>

          <div className="mt-4 space-y-4">
            {items.map((item, index) => (
              <div key={index} className="rounded-md border border-iron-100 p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div className="text-sm font-semibold text-iron-950">Quantity {index + 1}</div>
                  <button type="button" onClick={() => removeItem(index)} disabled={items.length <= 1} className="inline-flex items-center gap-2 text-sm text-red-700">
                    <Trash2 className="h-4 w-4" /> Remove
                  </button>
                </div>
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
                  <Input label="Code" value={item.code ?? ""} onChange={(value) => updateItem(index, { code: value })} />
                  <Input label="Description" value={item.description} onChange={(value) => updateItem(index, { description: value })} />
                  <Select label="Category" value={item.category} options={categories} onChange={(value) => updateItem(index, { category: value as QuantityCategory })} />
                  <Input label="Quantity" type="number" value={String(item.quantity)} onChange={(value) => updateItem(index, { quantity: Number(value) })} />
                  <Select label="Unit" value={item.unit} options={units} onChange={(value) => updateItem(index, { unit: value as QuantityUnit })} />
                  <Select label="Source" value={item.source} options={sources} onChange={(value) => updateItem(index, { source: value as QuantitySource })} />
                  <Input label="Confidence 0-1" type="number" value={String(item.confidence)} onChange={(value) => updateItem(index, { confidence: Number(value) })} />
                  <Input label="Drawing ref" value={item.drawing_reference ?? ""} onChange={(value) => updateItem(index, { drawing_reference: value })} />
                  <Input label="Notes" value={item.notes ?? ""} onChange={(value) => updateItem(index, { notes: value })} />
                  <label className="flex items-end gap-2 pb-2 text-sm font-medium text-iron-700">
                    <input type="checkbox" checked={item.estimate_ready} onChange={(event) => updateItem(index, { estimate_ready: event.target.checked })} />
                    Estimate ready
                  </label>
                </div>
              </div>
            ))}
          </div>
        </div>

        {error ? <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}

        <button type="submit" disabled={isLoading} className="inline-flex items-center gap-2 rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white">
          {isLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Calculator className="h-4 w-4" />}
          Summarize quantities
        </button>
      </form>

      {summary ? <QuantitySummary summary={summary} /> : null}
    </section>
  );
}

function QuantitySummary({ summary }: { summary: QuantityRegisterResponse }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <SummaryCard label="Items" value={String(summary.item_count)} />
        <SummaryCard label="Estimate Ready" value={String(summary.estimate_ready_count)} />
        <SummaryCard label="Low Confidence" value={String(summary.low_confidence_count)} />
      </div>

      {summary.warnings.length ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <div className="font-semibold">Quantity warnings</div>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {summary.warnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        </div>
      ) : null}

      <div className="overflow-hidden rounded-md border border-iron-100 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-iron-50 text-xs uppercase tracking-wide text-iron-500">
            <tr>
              <th className="px-3 py-2">Category</th>
              <th className="px-3 py-2">Unit</th>
              <th className="px-3 py-2">Total</th>
              <th className="px-3 py-2">Items</th>
              <th className="px-3 py-2">Estimate Ready</th>
            </tr>
          </thead>
          <tbody>
            {summary.summaries.map((line) => (
              <tr key={`${line.category}-${line.unit}`} className="border-t border-iron-100">
                <td className="px-3 py-2 font-medium text-iron-950">{line.category}</td>
                <td className="px-3 py-2 text-iron-700">{line.unit}</td>
                <td className="px-3 py-2 text-iron-700">{line.total_quantity}</td>
                <td className="px-3 py-2 text-iron-700">{line.item_count}</td>
                <td className="px-3 py-2 text-iron-700">{line.estimate_ready_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
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

function Select({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label className="grid gap-1 text-sm">
      <span className="font-medium text-iron-700">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="rounded-md border border-iron-100 px-3 py-2">
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md border border-iron-100 bg-white p-4"><div className="text-sm font-medium text-iron-500">{label}</div><div className="mt-2 text-2xl font-semibold text-iron-950">{value}</div></div>;
}
