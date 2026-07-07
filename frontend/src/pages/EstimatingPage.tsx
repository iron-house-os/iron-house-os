import { Calculator, Download, Plus, RefreshCw, Trash2 } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";

import {
  DefaultProductionActivity,
  EstimateCreate,
  EstimateLineItem,
  EstimateSummary,
  EstimateUnit,
  ProductionRate,
  estimatesApi,
} from "../api/estimates";
import { ProjectScopeNotice } from "../components/ProjectScopeNotice";
import { readProjectContext } from "../utils/projectContext";

const defaultLineItem: EstimateLineItem = {
  code: "31-001",
  description: "Excavation",
  item_type: "self_perform",
  quantity: 100,
  unit: "m3",
  default_activity: "excavation",
  labour: [],
  equipment: [],
  materials: [],
  vendor_quotes: [],
  direct_unit_cost: null,
};

const activityLabels: Record<DefaultProductionActivity, string> = {
  pipe_installation: "Pipe installation",
  excavation: "Excavation",
  bedding: "Bedding",
  backfill: "Backfill",
  asphalt_removal: "Asphalt removal",
  concrete_removal: "Concrete removal",
  manhole_installation: "Manhole installation",
  catch_basin_installation: "Catch basin installation",
  sidewalk: "Sidewalk",
  curb: "Curb",
  traffic_control: "Traffic control",
  landscaping: "Landscaping",
};

const moneyFormatter = new Intl.NumberFormat("en-CA", {
  style: "currency",
  currency: "CAD",
  maximumFractionDigits: 0,
});

export function EstimatingPage() {
  const location = useLocation();
  const projectContext = readProjectContext(location.search);
  const [projectName, setProjectName] = useState(projectContext.projectName ?? "Marine Drive Parking Lot");
  const [projectCode, setProjectCode] = useState(projectContext.projectId ?? "WR26-012");
  const [lineItems, setLineItems] = useState<EstimateLineItem[]>([defaultLineItem]);
  const [contingency, setContingency] = useState(10);
  const [overhead, setOverhead] = useState(5);
  const [profit, setProfit] = useState(10);
  const [bonding, setBonding] = useState(0);
  const [insurance, setInsurance] = useState(0);
  const [mobilization, setMobilization] = useState(1000);
  const [riskAmount, setRiskAmount] = useState(500);
  const [rateLibrary, setRateLibrary] = useState<ProductionRate[]>([]);
  const [summary, setSummary] = useState<EstimateSummary | null>(null);
  const [isLoadingRates, setIsLoadingRates] = useState(true);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (projectContext.projectName) setProjectName(projectContext.projectName);
    if (projectContext.projectId) setProjectCode(projectContext.projectId);
  }, [projectContext.projectId, projectContext.projectName]);

  const payload = useMemo<EstimateCreate>(
    () => ({
      project_name: projectName,
      project_code: projectCode,
      line_items: lineItems,
      indirects: [{ description: "Mobilization", amount: mobilization, category: "mobilization" }],
      risks: [{ description: "Unknown utilities / site conditions", amount: riskAmount }],
      markup: {
        contingency_percent: contingency,
        overhead_percent: overhead,
        profit_percent: profit,
        bonding_percent: bonding,
        insurance_percent: insurance,
      },
      assumptions: ["Normal working hours", "No contaminated soils unless noted"],
      exclusions: ["Permits, bonds, and design fees unless listed"],
    }),
    [bonding, contingency, insurance, lineItems, mobilization, overhead, profit, projectCode, projectName, riskAmount],
  );

  useEffect(() => {
    async function loadRates() {
      setIsLoadingRates(true);
      setError(null);
      try {
        const result = await estimatesApi.rateLibrary();
        setRateLibrary(result.production_rates);
      } catch (currentError) {
        setError(currentError instanceof Error ? currentError.message : "Unable to load rates");
      } finally {
        setIsLoadingRates(false);
      }
    }

    void loadRates();
  }, []);

  async function calculateEstimate(event?: FormEvent) {
    event?.preventDefault();
    setIsCalculating(true);
    setError(null);
    try {
      const result = await estimatesApi.summary(payload);
      setSummary(result);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to calculate estimate");
    } finally {
      setIsCalculating(false);
    }
  }

  function updateLineItem(index: number, patch: Partial<EstimateLineItem>) {
    setLineItems((items) => items.map((item, currentIndex) => (currentIndex === index ? { ...item, ...patch } : item)));
  }

  function addLineItem() {
    setLineItems((items) => [
      ...items,
      {
        ...defaultLineItem,
        code: `31-${String(items.length + 1).padStart(3, "0")}`,
        description: "New estimate item",
        quantity: 1,
        direct_unit_cost: 0,
        default_activity: null,
      },
    ]);
  }

  function removeLineItem(index: number) {
    setLineItems((items) => items.filter((_, currentIndex) => currentIndex !== index));
  }

  async function downloadWorkbook() {
    setError(null);
    try {
      const response = await fetch(estimatesApi.workbookUrl(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error(`Workbook request failed with ${response.status}`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${projectCode || projectName}_Estimate.xlsx`.replaceAll(" ", "_");
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to download workbook");
    }
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-iron-100 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-iron-950">Estimating</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">Build a first-pass Iron House estimate using production activity defaults, markups, risk, indirects, and workbook export.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => void calculateEstimate()} className="inline-flex items-center gap-2 rounded-md bg-iron-950 px-3 py-2 text-sm font-medium text-white"><Calculator className="h-4 w-4" /> Calculate</button>
          <button type="button" onClick={() => void downloadWorkbook()} className="inline-flex items-center gap-2 rounded-md border border-iron-100 bg-white px-3 py-2 text-sm font-medium text-iron-800"><Download className="h-4 w-4" /> Workbook</button>
        </div>
      </div>

      <ProjectScopeNotice name={projectContext.projectName} />
      {error ? <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}

      <form onSubmit={(event) => void calculateEstimate(event)} className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <div className="space-y-6">
          <div className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-iron-950">Project</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <label className="space-y-1 text-sm font-medium text-iron-700">Project name<input value={projectName} onChange={(event) => setProjectName(event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" /></label>
              <label className="space-y-1 text-sm font-medium text-iron-700">Project code<input value={projectCode} onChange={(event) => setProjectCode(event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" /></label>
            </div>
          </div>

          <div className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3"><div><h2 className="text-lg font-semibold text-iron-950">Line Items</h2><p className="text-sm text-iron-500">Choose a production activity or enter direct unit cost for quote/manual pricing.</p></div><button type="button" onClick={addLineItem} className="inline-flex items-center gap-2 rounded-md border border-iron-100 px-3 py-2 text-sm font-medium"><Plus className="h-4 w-4" /> Add</button></div>
            <div className="mt-4 space-y-4">
              {lineItems.map((item, index) => (
                <div key={`${item.code}-${index}`} className="rounded-lg border border-iron-100 p-4">
                  <div className="grid gap-3 md:grid-cols-[120px_1fr_120px_120px]"><input value={item.code ?? ""} onChange={(event) => updateLineItem(index, { code: event.target.value })} className="rounded-md border border-iron-100 px-3 py-2 text-sm" placeholder="Code" /><input value={item.description} onChange={(event) => updateLineItem(index, { description: event.target.value })} className="rounded-md border border-iron-100 px-3 py-2 text-sm" placeholder="Description" /><input type="number" value={item.quantity} onChange={(event) => updateLineItem(index, { quantity: Number(event.target.value) })} className="rounded-md border border-iron-100 px-3 py-2 text-sm" placeholder="Qty" /><select value={item.unit} onChange={(event) => updateLineItem(index, { unit: event.target.value as EstimateUnit })} className="rounded-md border border-iron-100 px-3 py-2 text-sm">{(["LS", "EA", "m", "m2", "m3", "t", "hr", "day"] as EstimateUnit[]).map((unit) => <option key={unit} value={unit}>{unit}</option>)}</select></div>
                  <div className="mt-3 grid gap-3 md:grid-cols-[1fr_160px_120px]"><select value={item.default_activity ?? ""} onChange={(event) => updateLineItem(index, { default_activity: event.target.value ? (event.target.value as DefaultProductionActivity) : null })} className="rounded-md border border-iron-100 px-3 py-2 text-sm"><option value="">No activity default</option>{rateLibrary.map((rate) => <option key={rate.activity} value={rate.activity}>{activityLabels[rate.activity]} — {rate.production_rate_per_hour}/hr</option>)}</select><input type="number" value={item.direct_unit_cost ?? ""} onChange={(event) => updateLineItem(index, { direct_unit_cost: event.target.value === "" ? null : Number(event.target.value) })} className="rounded-md border border-iron-100 px-3 py-2 text-sm" placeholder="Direct $/unit" /><button type="button" onClick={() => removeLineItem(index)} className="inline-flex items-center justify-center gap-2 rounded-md border border-iron-100 px-3 py-2 text-sm text-red-700"><Trash2 className="h-4 w-4" /> Remove</button></div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <aside className="space-y-6">
          <div className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm"><h2 className="text-lg font-semibold text-iron-950">Bid Build-Up</h2><div className="mt-4 grid gap-3"><NumberField label="Mobilization" value={mobilization} onChange={setMobilization} /><NumberField label="Risk allowance" value={riskAmount} onChange={setRiskAmount} /><NumberField label="Contingency %" value={contingency} onChange={setContingency} /><NumberField label="Overhead %" value={overhead} onChange={setOverhead} /><NumberField label="Profit %" value={profit} onChange={setProfit} /><NumberField label="Bonding %" value={bonding} onChange={setBonding} /><NumberField label="Insurance %" value={insurance} onChange={setInsurance} /></div></div>
          <div className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm"><div className="flex items-center justify-between"><h2 className="text-lg font-semibold text-iron-950">Summary</h2>{isCalculating || isLoadingRates ? <RefreshCw className="h-4 w-4 animate-spin" /> : null}</div>{summary ? <dl className="mt-4 space-y-3 text-sm"><SummaryRow label="Direct" value={summary.direct_cost} /><SummaryRow label="Indirect" value={summary.indirect_cost} /><SummaryRow label="Risk" value={summary.risk_cost} /><SummaryRow label="Contingency" value={summary.contingency} /><SummaryRow label="Overhead" value={summary.overhead} /><SummaryRow label="Profit" value={summary.profit} /><div className="border-t border-iron-100 pt-3"><SummaryRow label="Final Bid" value={summary.final_price} strong /></div><div className="flex justify-between text-iron-500"><dt>Gross margin</dt><dd>{summary.gross_margin_percent.toFixed(2)}%</dd></div></dl> : <p className="mt-4 text-sm text-iron-500">Calculate the estimate to view bid totals.</p>}</div>
        </aside>
      </form>
    </section>
  );
}

function NumberField({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return <label className="flex items-center justify-between gap-3 text-sm font-medium text-iron-700">{label}<input type="number" value={value} onChange={(event) => onChange(Number(event.target.value))} className="w-28 rounded-md border border-iron-100 px-3 py-2 text-right text-sm" /></label>;
}

function SummaryRow({ label, value, strong = false }: { label: string; value: number; strong?: boolean }) {
  return <div className={`flex justify-between ${strong ? "text-base font-semibold text-iron-950" : "text-iron-700"}`}><dt>{label}</dt><dd>{moneyFormatter.format(value)}</dd></div>;
}
