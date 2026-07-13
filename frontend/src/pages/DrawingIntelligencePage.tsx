import { FileSearch, RefreshCw, UploadCloud } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

import {
  CivilDrawingAnalysis,
  DrawingIssue,
  drawingIntelligenceApi,
} from "../api/drawingIntelligence";
import { ProjectScopeNotice } from "../components/ProjectScopeNotice";
import { readProjectContext } from "../utils/projectContext";

export function DrawingIntelligencePage() {
  const location = useLocation();
  const projectContext = readProjectContext(location.search);
  const [projectId, setProjectId] = useState(projectContext.projectId ?? "");
  const [title, setTitle] = useState("");
  const [municipality, setMunicipality] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [analyses, setAnalyses] = useState<CivilDrawingAnalysis[]>([]);
  const [result, setResult] = useState<CivilDrawingAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProjectAnalyses = useCallback(async () => {
    if (!projectId.trim()) {
      setAnalyses([]);
      return;
    }
    setError(null);
    try {
      const payload = await drawingIntelligenceApi.projectAnalyses(projectId.trim());
      setAnalyses(payload.items);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to load drawing analyses");
    }
  }, [projectId]);

  useEffect(() => {
    void loadProjectAnalyses();
  }, [loadProjectAnalyses]);

  async function ingest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || !projectId.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const analysis = await drawingIntelligenceApi.ingest({
        file,
        project_id: projectId.trim(),
        title: title.trim() || undefined,
        municipality: municipality.trim() || undefined,
      });
      setResult(analysis);
      setAnalyses((current) => [
        analysis,
        ...current.filter((item) => item.source.document_id !== analysis.source.document_id),
      ]);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to analyze the civil PDF");
    } finally {
      setIsLoading(false);
    }
  }

  async function reanalyze() {
    if (!result) return;
    setIsLoading(true);
    setError(null);
    try {
      const analysis = await drawingIntelligenceApi.reanalyze(
        result.source.document_id,
        municipality.trim() || undefined,
      );
      setResult(analysis);
      setAnalyses((current) => current.map((item) =>
        item.source.document_id === analysis.source.document_id ? analysis : item,
      ));
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to reanalyze the PDF");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-iron-100 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-iron-950">Drawing Intelligence</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
            Ingest project civil PDFs, retain their source hash and page evidence, surface quantity candidates, and flag constructability or municipal-standard review items.
          </p>
        </div>
        <button type="button" onClick={() => void loadProjectAnalyses()} className="inline-flex items-center gap-2 rounded-md border border-iron-100 bg-white px-3 py-2 text-sm font-semibold text-iron-800">
          <RefreshCw className="h-4 w-4" /> Refresh analyses
        </button>
      </div>

      <ProjectScopeNotice name={projectContext.projectName} />
      <div className="rounded-md border border-blue-200 bg-blue-50 p-4 text-sm leading-6 text-blue-800">
        Evidence-first workflow: extracted quantities are candidates, never approved takeoff values. Scanned pages are marked for OCR, and municipal references require human compliance review.
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <form onSubmit={ingest} className="rounded-md border border-iron-100 bg-white p-5">
          <div className="flex items-center gap-2">
            <UploadCloud className="h-5 w-5 text-signal-blue" />
            <h2 className="text-base font-semibold text-iron-950">Ingest civil PDF</h2>
          </div>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <Field label="Project ID">
              <input aria-label="Drawing project ID" required value={projectId} onChange={(event) => setProjectId(event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" placeholder="Project UUID" />
            </Field>
            <Field label="Municipality">
              <input aria-label="Drawing municipality" value={municipality} onChange={(event) => setMunicipality(event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" placeholder="Surrey" />
            </Field>
            <Field label="Drawing-set title">
              <input aria-label="Drawing set title" value={title} onChange={(event) => setTitle(event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" placeholder="Issued for Tender Civil Drawings" />
            </Field>
            <Field label="Civil PDF">
              <input aria-label="Civil PDF file" type="file" accept="application/pdf,.pdf" onChange={(event) => setFile(event.target.files?.[0] ?? null)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" />
            </Field>
          </div>
          {file ? <p className="mt-3 text-xs text-iron-500">Selected: {file.name}</p> : null}
          {error ? <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
          <button type="submit" disabled={isLoading || !file || !projectId.trim()} className="mt-4 inline-flex items-center gap-2 rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white disabled:bg-iron-300">
            {isLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <FileSearch className="h-4 w-4" />}
            Ingest and analyze PDF
          </button>
        </form>

        <div className="rounded-md border border-iron-100 bg-white p-5">
          <h2 className="text-base font-semibold text-iron-950">Project analyses</h2>
          <p className="mt-1 text-sm text-iron-500">Persisted reports for the selected project.</p>
          <div className="mt-4 space-y-2">
            {analyses.length ? analyses.map((analysis) => (
              <button key={analysis.source.document_id} type="button" onClick={() => setResult(analysis)} className="w-full rounded-md border border-iron-100 p-3 text-left hover:border-iron-500">
                <div className="text-sm font-semibold text-iron-950">{analysis.title}</div>
                <div className="mt-1 text-xs text-iron-500">{analysis.source.page_count} pages · {analysis.extraction_status}</div>
              </button>
            )) : <p className="text-sm text-iron-500">No analyzed civil PDFs for this project.</p>}
          </div>
        </div>
      </div>

      {result ? <AnalysisReport result={result} isLoading={isLoading} onReanalyze={() => void reanalyze()} /> : null}
    </section>
  );
}

function AnalysisReport({
  result,
  isLoading,
  onReanalyze,
}: {
  result: CivilDrawingAnalysis;
  isLoading: boolean;
  onReanalyze: () => void;
}) {
  const reviewCount = result.constructability_issues.length + result.municipal_standard_issues.length;
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 rounded-md border border-iron-100 bg-white p-5 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide text-iron-500">Analyzed source</div>
          <h2 className="mt-1 text-xl font-semibold text-iron-950">{result.title}</h2>
          <p className="mt-1 text-xs text-iron-500">{result.source.original_filename} · SHA-256 {result.source.sha256_hash}</p>
        </div>
        <button type="button" disabled={isLoading} onClick={onReanalyze} className="rounded-md border border-iron-100 px-3 py-2 text-sm font-semibold disabled:text-iron-300">Reanalyze stored PDF</button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <SummaryCard label="Extraction" value={result.extraction_status} />
        <SummaryCard label="Pages" value={String(result.source.page_count)} />
        <SummaryCard label="Quantity candidates" value={String(result.quantity_candidates.length)} />
        <SummaryCard label="Review flags" value={String(reviewCount)} />
      </div>

      {result.warnings.map((warning) => (
        <div key={warning} className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{warning}</div>
      ))}

      <div className="rounded-md border border-iron-100 bg-white p-5">
        <h3 className="text-base font-semibold text-iron-950">Quantity candidates</h3>
        <p className="mt-1 text-sm text-iron-500">Candidate quantities require verification against the PDF, scale, notes, and applicable takeoff rules.</p>
        {result.quantity_candidates.length ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-iron-50 text-xs uppercase tracking-wide text-iron-500"><tr><th className="px-3 py-2">Description</th><th className="px-3 py-2">Quantity</th><th className="px-3 py-2">Page</th><th className="px-3 py-2">Confidence</th></tr></thead>
              <tbody>{result.quantity_candidates.map((candidate, index) => (
                <tr key={`${candidate.page_number}-${candidate.quantity}-${index}`} className="border-t border-iron-100"><td className="px-3 py-2 text-iron-700">{candidate.description}</td><td className="px-3 py-2 font-semibold text-iron-950">{candidate.quantity} {candidate.unit}</td><td className="px-3 py-2 text-iron-700">{candidate.page_number}</td><td className="px-3 py-2 text-iron-700">{candidate.confidence}</td></tr>
              ))}</tbody>
            </table>
          </div>
        ) : <p className="mt-4 text-sm text-iron-500">No explicit civil quantity candidates were found in embedded text.</p>}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <IssueList title="Constructability review" issues={result.constructability_issues} />
        <IssueList title="Municipal standards review" issues={result.municipal_standard_issues} />
      </div>

      <div className="rounded-md border border-iron-100 bg-white p-5">
        <h3 className="text-base font-semibold text-iron-950">Page extraction trace</h3>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {result.pages.map((page) => (
            <div key={page.page_number} className="rounded-md border border-iron-100 p-3">
              <div className="text-sm font-semibold text-iron-950">Page {page.page_number} · {page.character_count} characters</div>
              <p className="mt-2 line-clamp-4 text-xs leading-5 text-iron-500">{page.text_preview ?? page.extraction_warning ?? "No text"}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function IssueList({ title, issues }: { title: string; issues: DrawingIssue[] }) {
  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <h3 className="text-base font-semibold text-iron-950">{title}</h3>
      <div className="mt-4 space-y-3">
        {issues.length ? issues.map((issue, index) => (
          <div key={`${issue.title}-${issue.page_number ?? index}`} className={`rounded-md border p-3 ${issue.severity === "critical" ? "border-red-200 bg-red-50" : issue.severity === "warning" ? "border-amber-200 bg-amber-50" : "border-blue-200 bg-blue-50"}`}>
            <div className="text-sm font-semibold text-iron-950">{issue.title}</div>
            <p className="mt-1 text-xs leading-5 text-iron-700">{issue.detail}</p>
            {issue.page_number ? <div className="mt-2 text-xs text-iron-500">Page {issue.page_number}</div> : null}
          </div>
        )) : <p className="text-sm text-iron-500">No automated flags detected; manual review is still required.</p>}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="mb-1 block text-sm font-medium text-iron-800">{label}</span>{children}</label>;
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md border border-iron-100 bg-white p-4"><div className="text-sm font-medium text-iron-500">{label}</div><div className="mt-2 text-xl font-semibold capitalize text-iron-950">{value}</div></div>;
}
