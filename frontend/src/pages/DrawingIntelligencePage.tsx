import { FileSearch, Plus, RefreshCw, Trash2 } from "lucide-react";
import { FormEvent, useState } from "react";

import {
  DrawingSetAnalysisResponse,
  DrawingSheetInput,
  drawingIntelligenceApi,
} from "../api/drawingIntelligence";

function blankSheet(): DrawingSheetInput {
  return {
    sheet_number: "C-001",
    title: "Civil Cover Sheet",
    filename: "C-001 Civil Cover Sheet Rev A.pdf",
    revision: "",
    scale: "",
    raw_text: "City of Surrey civil drawings issued for tender revision A",
  };
}

export function DrawingIntelligencePage() {
  const [projectName, setProjectName] = useState("Iron House Tender Review");
  const [municipality, setMunicipality] = useState("");
  const [sheets, setSheets] = useState<DrawingSheetInput[]>([
    blankSheet(),
    {
      sheet_number: "C-101",
      title: "Roadworks and Utility Plan",
      filename: "C-101 Roadworks Utility Plan.pdf",
      scale: "1:250",
      raw_text: "storm sanitary watermain roadworks utility plan 1:250",
    },
    {
      sheet_number: "C-201",
      title: "Plan and Profile",
      filename: "C-201 Plan and Profile.pdf",
      raw_text: "plan and profile sanitary storm watermain",
    },
  ]);
  const [result, setResult] = useState<DrawingSetAnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function analyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      setResult(
        await drawingIntelligenceApi.analyze({
          project_name: projectName,
          municipality: municipality || null,
          sheets: sheets.filter((sheet) => sheet.title.trim()),
        }),
      );
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to analyze drawings");
    } finally {
      setIsLoading(false);
    }
  }

  function updateSheet(index: number, patch: Partial<DrawingSheetInput>) {
    setSheets((current) => current.map((sheet, currentIndex) => (currentIndex === index ? { ...sheet, ...patch } : sheet)));
  }

  function removeSheet(index: number) {
    setSheets((current) => current.filter((_, currentIndex) => currentIndex !== index));
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-iron-100 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-iron-950">Drawing Intelligence</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
            Build 24 core metadata engine: classify sheets, detect revisions, scales, municipalities, duplicates, and missing drawing-set signals.
          </p>
        </div>
      </div>

      <form className="space-y-6" onSubmit={analyze}>
        <div className="rounded-md border border-iron-100 bg-white p-5">
          <h2 className="text-base font-semibold text-iron-950">Drawing Set</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <Input label="Project name" value={projectName} onChange={setProjectName} />
            <Input label="Municipality" value={municipality} onChange={setMunicipality} />
          </div>
        </div>

        <div className="rounded-md border border-iron-100 bg-white p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-iron-950">Sheet Register</h2>
              <p className="mt-1 text-sm text-iron-500">Enter sheet metadata now. OCR/PDF ingestion can populate this later.</p>
            </div>
            <button type="button" onClick={() => setSheets((current) => [...current, blankSheet()])} className="inline-flex items-center gap-2 rounded-md border border-iron-100 px-3 py-2 text-sm font-semibold text-iron-800">
              <Plus className="h-4 w-4" /> Add sheet
            </button>
          </div>

          <div className="mt-4 space-y-4">
            {sheets.map((sheet, index) => (
              <div key={index} className="rounded-md border border-iron-100 p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div className="text-sm font-semibold text-iron-950">Sheet {index + 1}</div>
                  <button type="button" onClick={() => removeSheet(index)} disabled={sheets.length <= 1} className="inline-flex items-center gap-2 text-sm text-red-700">
                    <Trash2 className="h-4 w-4" /> Remove
                  </button>
                </div>
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
                  <Input label="Sheet #" value={sheet.sheet_number ?? ""} onChange={(value) => updateSheet(index, { sheet_number: value })} />
                  <Input label="Title" value={sheet.title} onChange={(value) => updateSheet(index, { title: value })} />
                  <Input label="Filename" value={sheet.filename ?? ""} onChange={(value) => updateSheet(index, { filename: value })} />
                  <Input label="Revision" value={sheet.revision ?? ""} onChange={(value) => updateSheet(index, { revision: value })} />
                  <Input label="Scale" value={sheet.scale ?? ""} onChange={(value) => updateSheet(index, { scale: value })} />
                </div>
                <label className="mt-3 grid gap-1 text-sm">
                  <span className="font-medium text-iron-700">Extracted / raw text</span>
                  <textarea value={sheet.raw_text ?? ""} onChange={(event) => updateSheet(index, { raw_text: event.target.value })} className="min-h-20 rounded-md border border-iron-100 px-3 py-2" />
                </label>
              </div>
            ))}
          </div>
        </div>

        {error ? <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}

        <button type="submit" disabled={isLoading} className="inline-flex items-center gap-2 rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white">
          {isLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <FileSearch className="h-4 w-4" />}
          Analyze drawing set
        </button>
      </form>

      {result ? <AnalysisResult result={result} /> : null}
    </section>
  );
}

function AnalysisResult({ result }: { result: DrawingSetAnalysisResponse }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        <SummaryCard label="Sheets" value={String(result.sheet_count)} />
        <SummaryCard label="Disciplines" value={String(Object.keys(result.disciplines).length)} />
        <SummaryCard label="Sheet Types" value={String(Object.keys(result.sheet_types).length)} />
        <SummaryCard label="Municipality Hints" value={result.municipality_hints.join(", ") || "None"} />
      </div>

      {result.warnings.length ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <div className="font-semibold">Drawing set warnings</div>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {result.warnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        </div>
      ) : null}

      <div className="overflow-hidden rounded-md border border-iron-100 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-iron-50 text-xs uppercase tracking-wide text-iron-500">
            <tr>
              <th className="px-3 py-2">Sheet</th>
              <th className="px-3 py-2">Title</th>
              <th className="px-3 py-2">Discipline</th>
              <th className="px-3 py-2">Type</th>
              <th className="px-3 py-2">Revision</th>
              <th className="px-3 py-2">Scale</th>
              <th className="px-3 py-2">Warnings</th>
            </tr>
          </thead>
          <tbody>
            {result.sheets.map((sheet, index) => (
              <tr key={`${sheet.sheet_number ?? "sheet"}-${index}`} className="border-t border-iron-100">
                <td className="px-3 py-2 font-medium text-iron-950">{sheet.sheet_number ?? "—"}</td>
                <td className="px-3 py-2 text-iron-700">{sheet.title}</td>
                <td className="px-3 py-2 text-iron-700">{sheet.discipline}</td>
                <td className="px-3 py-2 text-iron-700">{sheet.sheet_type}</td>
                <td className="px-3 py-2 text-iron-700">{sheet.revision ?? "—"}</td>
                <td className="px-3 py-2 text-iron-700">{sheet.scale ?? "—"}</td>
                <td className="px-3 py-2 text-iron-700">{sheet.warnings.join(", ") || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Input({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label className="grid gap-1 text-sm"><span className="font-medium text-iron-700">{label}</span><input value={value} onChange={(event) => onChange(event.target.value)} className="rounded-md border border-iron-100 px-3 py-2" /></label>;
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md border border-iron-100 bg-white p-4"><div className="text-sm font-medium text-iron-500">{label}</div><div className="mt-2 text-xl font-semibold text-iron-950">{value}</div></div>;
}
