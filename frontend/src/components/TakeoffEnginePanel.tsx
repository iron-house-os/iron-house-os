import { useState } from "react";

import { estimatesApi, EstimateHandoffResponse } from "../api/estimates";
import {
  DrawingSheetInput,
  QuantityItem,
  TakeoffEngineResponse,
  TakeoffExtractionRule,
  takeoffApi,
} from "../api/takeoff";

type Props = {
  projectName?: string | null;
  projectId?: string | null;
  manualItems: QuantityItem[];
};

export function TakeoffEnginePanel({ projectName, projectId, manualItems }: Props) {
  const [result, setResult] = useState<TakeoffEngineResponse | null>(null);
  const [handoff, setHandoff] = useState<EstimateHandoffResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isHandoffLoading, setIsHandoffLoading] = useState(false);

  async function runEngine() {
    const sheets: DrawingSheetInput[] = [
      { sheet_number: "C-101", title: "Civil plan", discipline: "civil", scale: "1:250", revision: "current" },
    ];
    const extractionRules: TakeoffExtractionRule[] = [
      {
        category: "asphalt",
        description: "Asphalt paving area",
        unit: "m2",
        method: "area_trace",
        drawing_reference: "C-101",
        measured_value: 250,
        multiplier: 1,
        waste_factor: 0.03,
        confidence: 0.82,
        notes: "Build 29 sample extraction rule; replace with measured takeoff value.",
      },
    ];

    setIsLoading(true);
    setError(null);
    setHandoff(null);
    try {
      setResult(
        await takeoffApi.runEngine({
          project_name: projectName,
          project_id: projectId,
          drawing_set_name: "Civil drawing set",
          sheets,
          extraction_rules: extractionRules,
          manual_items: manualItems,
        }),
      );
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to run takeoff engine");
    } finally {
      setIsLoading(false);
    }
  }

  async function sendToEstimating() {
    if (!result) return;
    setIsHandoffLoading(true);
    setError(null);
    try {
      setHandoff(
        await estimatesApi.handoff({
          project_name: projectName || "Iron House Estimate",
          project_code: projectId,
          items: result.estimating_handoff_items.map((item) => ({
            code: item.code,
            description: item.description,
            category: item.category,
            quantity: item.quantity,
            unit: item.unit,
            source: item.source,
            confidence: item.confidence,
            drawing_reference: item.drawing_reference,
            notes: item.notes,
          })),
        }),
      );
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to build estimating handoff");
    } finally {
      setIsHandoffLoading(false);
    }
  }

  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-base font-semibold text-iron-950">Build 29/30 Takeoff to Estimate</h2>
          <p className="mt-1 text-sm text-iron-500">
            Runs takeoff, creates estimate-ready BOQ items, then converts those quantities into estimating line items.
          </p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={runEngine} disabled={isLoading} className="rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white">
            {isLoading ? "Running..." : "Run engine"}
          </button>
          <button type="button" onClick={sendToEstimating} disabled={!result || isHandoffLoading} className="rounded-md border border-iron-100 px-4 py-2 text-sm font-semibold text-iron-800">
            {isHandoffLoading ? "Sending..." : "Send to estimating"}
          </button>
        </div>
      </div>

      {error ? <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}

      {result ? (
        <div className="mt-5 space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <Metric label="Sheets" value={result.sheets_reviewed} />
            <Metric label="Generated" value={result.generated_items.length} />
            <Metric label="Handoff" value={result.estimating_handoff_items.length} />
            <Metric label="Conflicts" value={result.conflicts.length} />
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            {result.readiness_checks.map((check) => (
              <div key={check.label} className="rounded-md border border-iron-100 p-3">
                <div className="text-sm font-semibold text-iron-950">{check.label}</div>
                <div className="mt-1 text-xs uppercase tracking-wide text-iron-500">{check.status}</div>
                <p className="mt-2 text-sm text-iron-600">{check.detail}</p>
              </div>
            ))}
          </div>

          <List title="Generated BOQ items" items={result.generated_items.map((item) => `${item.code}: ${item.description} - ${item.quantity} ${item.unit}`)} />
          <List title="Conflicts" items={result.conflicts} />
          <List title="Next actions" items={result.next_actions} />
        </div>
      ) : null}

      {handoff ? (
        <div className="mt-5 space-y-4 rounded-md border border-iron-100 p-4">
          <div className="font-semibold text-iron-950">Estimate handoff created</div>
          <div className="grid gap-4 md:grid-cols-2">
            <Metric label="Estimate lines" value={handoff.line_items.length} />
            <Metric label="Warnings" value={handoff.warnings.length} />
          </div>
          <List title="Estimate line items" items={handoff.line_items.map((item) => `${item.code}: ${item.description} - ${item.quantity} ${item.unit} (${item.item_type})`)} />
          <List title="Handoff warnings" items={handoff.warnings} />
          <List title="Handoff assumptions" items={handoff.assumptions} />
        </div>
      ) : null}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-md border border-iron-100 p-3"><div className="text-xs uppercase tracking-wide text-iron-500">{label}</div><div className="mt-1 text-xl font-semibold text-iron-950">{value}</div></div>;
}

function List({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return <div className="rounded-md border border-iron-100 p-3 text-sm text-iron-700"><div className="font-semibold text-iron-950">{title}</div><ul className="mt-2 list-disc space-y-1 pl-5">{items.map((item) => <li key={item}>{item}</li>)}</ul></div>;
}
