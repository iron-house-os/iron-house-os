import { FileText, RefreshCw } from "lucide-react";
import { FormEvent, useState } from "react";
import { useLocation } from "react-router-dom";

import {
  BidPackageGenerateResponse,
  BidPackageInputItem,
  BidPackageSection,
  ReadinessStatus,
  bidPackageApi,
} from "../api/bidPackage";
import { ProjectScopeNotice } from "../components/ProjectScopeNotice";
import { readProjectContext } from "../utils/projectContext";

const sections: BidPackageSection[] = [
  "executive_summary",
  "scope_of_work",
  "assumptions",
  "exclusions",
  "risks",
  "municipality_requirements",
  "quantities",
  "rfq_status",
  "supplier_coverage",
  "documents",
];
const statuses: ReadinessStatus[] = ["ready", "needs_review", "missing"];

function defaultItems(): BidPackageInputItem[] {
  return sections.map((section) => ({
    section,
    title: titleCase(section),
    status: section === "rfq_status" || section === "supplier_coverage" ? "needs_review" : "ready",
    content: section === "scope_of_work" ? "Civil construction scope based on tender drawings, specifications, addenda, estimate, and RFQ responses." : "",
    source: "manual",
  }));
}

export function BidPackageGeneratorPage() {
  const location = useLocation();
  const projectContext = readProjectContext(location.search);
  const [projectName, setProjectName] = useState(projectContext.projectName ?? "Iron House Tender Review");
  const [municipality, setMunicipality] = useState("Surrey");
  const [bidDueDate, setBidDueDate] = useState("");
  const [estimatedPrice, setEstimatedPrice] = useState(0);
  const [items, setItems] = useState<BidPackageInputItem[]>(defaultItems());
  const [result, setResult] = useState<BidPackageGenerateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      setResult(
        await bidPackageApi.generate({
          project_name: projectName,
          municipality,
          bid_due_date: bidDueDate || null,
          estimated_price: estimatedPrice || null,
          items,
        }),
      );
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to generate bid package");
    } finally {
      setIsLoading(false);
    }
  }

  function updateItem(index: number, patch: Partial<BidPackageInputItem>) {
    setItems((current) => current.map((item, currentIndex) => (currentIndex === index ? { ...item, ...patch } : item)));
  }

  return (
    <section className="space-y-6">
      <div className="border-b border-iron-100 pb-6">
        <h1 className="text-3xl font-semibold text-iron-950">Bid Package Generator</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
          Build 28 review package generator with readiness scoring, checklist, assumptions, exclusions, risks, and bid summary.
        </p>
      </div>

      <ProjectScopeNotice name={projectContext.projectName} />

      <form className="space-y-6" onSubmit={generate}>
        <div className="rounded-md border border-iron-100 bg-white p-5">
          <h2 className="text-base font-semibold text-iron-950">Bid setup</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-4">
            <Input label="Project name" value={projectName} onChange={setProjectName} />
            <Input label="Municipality" value={municipality} onChange={setMunicipality} />
            <Input label="Bid due date" type="date" value={bidDueDate} onChange={setBidDueDate} />
            <Input label="Estimated price" type="number" value={String(estimatedPrice)} onChange={(value) => setEstimatedPrice(Number(value))} />
          </div>
        </div>

        <div className="rounded-md border border-iron-100 bg-white p-5">
          <h2 className="text-base font-semibold text-iron-950">Package sections</h2>
          <div className="mt-4 space-y-4">
            {items.map((item, index) => (
              <div key={item.section} className="rounded-md border border-iron-100 p-4">
                <div className="grid gap-3 lg:grid-cols-[220px_160px_1fr]">
                  <div>
                    <div className="text-xs uppercase tracking-wide text-iron-500">{item.section}</div>
                    <input value={item.title} onChange={(event) => updateItem(index, { title: event.target.value })} className="mt-1 w-full rounded-md border border-iron-100 px-3 py-2 text-sm font-semibold text-iron-950" />
                  </div>
                  <label className="grid gap-1 text-sm">
                    <span className="font-medium text-iron-700">Status</span>
                    <select value={item.status} onChange={(event) => updateItem(index, { status: event.target.value as ReadinessStatus })} className="rounded-md border border-iron-100 px-3 py-2">
                      {statuses.map((status) => <option key={status} value={status}>{status}</option>)}
                    </select>
                  </label>
                  <label className="grid gap-1 text-sm">
                    <span className="font-medium text-iron-700">Content / note</span>
                    <textarea value={item.content ?? ""} onChange={(event) => updateItem(index, { content: event.target.value })} className="min-h-16 rounded-md border border-iron-100 px-3 py-2" />
                  </label>
                </div>
              </div>
            ))}
          </div>
        </div>

        {error ? <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}

        <button type="submit" disabled={isLoading} className="inline-flex items-center gap-2 rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white">
          {isLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
          Generate bid package
        </button>
      </form>

      {result ? <BidPackageResult result={result} /> : null}
    </section>
  );
}

function BidPackageResult({ result }: { result: BidPackageGenerateResponse }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        <SummaryCard label="Readiness" value={`${result.summary.readiness_score}%`} />
        <SummaryCard label="Ready" value={String(result.summary.ready_count)} />
        <SummaryCard label="Needs Review" value={String(result.summary.needs_review_count)} />
        <SummaryCard label="Missing" value={String(result.summary.missing_count)} />
      </div>

      <div className="rounded-md border border-iron-100 bg-white p-5">
        <h2 className="text-base font-semibold text-iron-950">Executive Summary</h2>
        <p className="mt-2 text-sm leading-6 text-iron-600">{result.executive_summary}</p>
      </div>

      {result.warnings.length ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <div className="font-semibold">Warnings</div>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {result.warnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-3">
        <ListPanel title="Scope of Work" items={result.scope_of_work} />
        <ListPanel title="Assumptions" items={result.assumptions} />
        <ListPanel title="Exclusions" items={result.exclusions} />
      </div>
      <ListPanel title="Risks" items={result.risks} />

      <div className="overflow-hidden rounded-md border border-iron-100 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-iron-50 text-xs uppercase tracking-wide text-iron-500">
            <tr>
              <th className="px-3 py-2">Section</th>
              <th className="px-3 py-2">Title</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Note</th>
            </tr>
          </thead>
          <tbody>
            {result.checklist.map((item) => (
              <tr key={item.section} className="border-t border-iron-100">
                <td className="px-3 py-2 text-iron-700">{item.section}</td>
                <td className="px-3 py-2 font-medium text-iron-950">{item.title}</td>
                <td className="px-3 py-2 text-iron-700">{item.status}</td>
                <td className="px-3 py-2 text-iron-700">{item.note}</td>
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

function ListPanel({ title, items }: { title: string; items: string[] }) {
  return <div className="rounded-md border border-iron-100 bg-white p-5"><h2 className="text-base font-semibold text-iron-950">{title}</h2><ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-iron-600">{items.map((item) => <li key={item}>{item}</li>)}</ul></div>;
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md border border-iron-100 bg-white p-4"><div className="text-sm font-medium text-iron-500">{label}</div><div className="mt-2 text-2xl font-semibold text-iron-950">{value}</div></div>;
}

function titleCase(value: string) {
  return value.split("_").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
}
