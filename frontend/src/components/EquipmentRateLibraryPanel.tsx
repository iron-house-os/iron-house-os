import { Calculator, Download } from "lucide-react";
import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";

import {
  EquipmentBenchmark,
  EquipmentRateInput,
  EquipmentRateLibrary,
  EquipmentRateResult,
  RegionalMarket,
  RentalPeriod,
  equipmentRatesApi,
} from "../api/equipmentRates";

const money = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" });

export function EquipmentRateLibraryPanel() {
  const [library, setLibrary] = useState<EquipmentRateLibrary | null>(null);
  const [selectedIndex, setSelectedIndex] = useState("");
  const [market, setMarket] = useState<RegionalMarket>("surrey_fraser_valley_east");
  const [period, setPeriod] = useState<RentalPeriod>("day");
  const [baseRate, setBaseRate] = useState("");
  const [includedHours, setIncludedHours] = useState("8");
  const [operatorCost, setOperatorCost] = useState("");
  const [sourceName, setSourceName] = useState("");
  const [result, setResult] = useState<EquipmentRateResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    equipmentRatesApi.library()
      .then(setLibrary)
      .catch((current) => setError(current instanceof Error ? current.message : "Unable to load rate library"));
  }, []);

  const benchmark = useMemo<EquipmentBenchmark | null>(() => {
    if (!library || selectedIndex === "") return null;
    return library.benchmarks[Number(selectedIndex)] ?? null;
  }, [library, selectedIndex]);

  function payload(): EquipmentRateInput | null {
    if (!benchmark || !baseRate || !sourceName.trim()) return null;
    return {
      regional_market: market,
      rate_category: benchmark.rate_category,
      equipment_class: benchmark.equipment_class,
      equipment_description: benchmark.equipment_description,
      ownership_basis: "rented",
      rate_basis: "vendor_quote",
      operator_included: false,
      base_rate: Number(baseRate),
      rental_period: period,
      included_hours: period === "hour" ? 1 : Number(includedHours),
      operator_hourly_cost: Number(operatorCost || 0),
      target_margin_percent: library?.default_target_margin_percent ?? 10,
      market_benchmark_rate: benchmark.base_rate,
      fuel_surcharge_percent: 0,
      source_name: sourceName.trim(),
    };
  }

  async function calculate(event: FormEvent) {
    event.preventDefault();
    const input = payload();
    if (!input) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await equipmentRatesApi.calculate(input));
    } catch (current) {
      setError(current instanceof Error ? current.message : "Unable to calculate rate");
    } finally {
      setBusy(false);
    }
  }

  async function exportDraft() {
    const input = payload();
    if (!input) return;
    setBusy(true);
    setError(null);
    try {
      const blob = await equipmentRatesApi.exportDraft(input);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "Iron_House_Client_Rate_Sheet_DRAFT.pdf";
      link.click();
      URL.revokeObjectURL(url);
    } catch (current) {
      setError(current instanceof Error ? current.message : "Unable to export draft rate sheet");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-md border border-iron-100 bg-white p-5" aria-labelledby="equipment-rate-heading">
      <div className="flex items-center gap-2">
        <Calculator className="h-4 w-4" />
        <h2 id="equipment-rate-heading" className="text-base font-semibold">Equipment and client rate library</h2>
      </div>
      <p className="mt-1 text-sm text-iron-500">
        Convert vendor rental periods to an auditable hourly cost, apply final margin, and compare it with the approved benchmark.
      </p>
      {error ? <div role="alert" className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
      <form onSubmit={calculate} className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <Select label="Regional market" value={market} onChange={(value) => setMarket(value as RegionalMarket)}>
          <option value="surrey_fraser_valley_east">Surrey / Fraser Valley East</option>
          <option value="vancouver_metro_west">Vancouver / Metro West</option>
        </Select>
        <Select label="Equipment class" value={selectedIndex} onChange={setSelectedIndex} required>
          <option value="">Select approved benchmark</option>
          {library?.benchmarks.map((item, index) => (
            <option key={`${item.rate_category}-${item.equipment_class}-${item.equipment_description}`} value={index}>
              {item.equipment_class} — {item.equipment_description}{item.base_rate == null ? " — price on request" : ` — ${money.format(item.base_rate)}/hr`}
            </option>
          ))}
        </Select>
        <Select label="Vendor rental period" value={period} onChange={(value) => setPeriod(value as RentalPeriod)}>
          <option value="hour">Hour</option><option value="day">Day</option><option value="week">Week</option><option value="month">Month</option>
        </Select>
        <NumberInput label="Vendor base rental" value={baseRate} onChange={setBaseRate} required />
        <NumberInput label="Included hours" value={period === "hour" ? "1" : includedHours} onChange={setIncludedHours} disabled={period === "hour"} required />
        <NumberInput label="Operator hourly direct cost" value={operatorCost} onChange={setOperatorCost} />
        <label className="grid gap-1 text-sm md:col-span-2 xl:col-span-3">
          <span className="font-medium text-iron-700">Vendor/source name</span>
          <input required value={sourceName} onChange={(event) => setSourceName(event.target.value)} className="rounded-md border border-iron-100 px-3 py-2" />
        </label>
        <div className="flex flex-wrap gap-2 md:col-span-2 xl:col-span-3">
          <button disabled={busy} type="submit" className="rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">Calculate controlled rate</button>
          <button disabled={busy || !result} type="button" onClick={() => void exportDraft()} className="inline-flex items-center gap-2 rounded-md border border-iron-100 px-4 py-2 text-sm font-semibold disabled:opacity-50"><Download className="h-4 w-4" /> Export draft PDF</button>
        </div>
      </form>
      {result ? (
        <div className="mt-5 grid gap-3 rounded-md bg-iron-50 p-4 sm:grid-cols-2 lg:grid-cols-4">
          <Result label="Hourly direct cost" value={money.format(result.hourly_all_in_direct_cost)} />
          <Result label="Calculated minimum" value={`${money.format(result.calculated_client_rate)}/hr`} />
          <Result label="Selected client rate" value={`${money.format(result.selected_client_rate)}/hr`} />
          <Result label="Minimum billable" value={money.format(result.minimum_billable_amount)} />
          {result.approval_required ? <div role="alert" className="sm:col-span-2 lg:col-span-4 text-sm font-semibold text-amber-800">Approval required: {result.approval_reasons.join(", ").replaceAll("_", " ")}</div> : null}
        </div>
      ) : null}
      <p className="mt-4 text-xs text-iron-500">Exports remain marked DRAFT until executive approval is recorded. Vancouver logistics and access premiums remain separate estimate lines.</p>
    </section>
  );
}

function Select({ label, value, onChange, required = false, children }: { label: string; value: string; onChange: (value: string) => void; required?: boolean; children: ReactNode }) {
  return <label className="grid gap-1 text-sm"><span className="font-medium text-iron-700">{label}</span><select required={required} value={value} onChange={(event) => onChange(event.target.value)} className="rounded-md border border-iron-100 px-3 py-2">{children}</select></label>;
}

function NumberInput({ label, value, onChange, required = false, disabled = false }: { label: string; value: string; onChange: (value: string) => void; required?: boolean; disabled?: boolean }) {
  return <label className="grid gap-1 text-sm"><span className="font-medium text-iron-700">{label}</span><input type="number" min="0" step="0.01" required={required} disabled={disabled} value={value} onChange={(event) => onChange(event.target.value)} className="rounded-md border border-iron-100 px-3 py-2 disabled:bg-iron-50" /></label>;
}

function Result({ label, value }: { label: string; value: string }) {
  return <div><div className="text-xs font-semibold uppercase tracking-wide text-iron-500">{label}</div><div className="mt-1 font-semibold text-iron-950">{value}</div></div>;
}
