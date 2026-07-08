import { AlertTriangle, CheckSquare, RefreshCw } from "lucide-react";
import { FormEvent, useState } from "react";
import { useLocation } from "react-router-dom";

import { MunicipalityCheckResponse, ProjectScope, municipalityApi } from "../api/municipality";
import { ProjectScopeNotice } from "../components/ProjectScopeNotice";
import { readProjectContext } from "../utils/projectContext";

const municipalities = ["Surrey", "Vancouver", "Burnaby", "Richmond", "Delta", "Langley", "Abbotsford", "Chilliwack", "Sechelt"];
const scopes: ProjectScope[] = ["water", "sanitary", "storm", "roadworks", "asphalt", "concrete", "traffic", "landscape", "earthworks"];

export function MunicipalityIntelligencePage() {
  const location = useLocation();
  const projectContext = readProjectContext(location.search);
  const [municipality, setMunicipality] = useState("Surrey");
  const [selectedScopes, setSelectedScopes] = useState<ProjectScope[]>(["storm", "roadworks", "asphalt", "traffic"]);
  const [result, setResult] = useState<MunicipalityCheckResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function check(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      setResult(await municipalityApi.check({ municipality, project_scopes: selectedScopes }));
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to check municipality requirements");
    } finally {
      setIsLoading(false);
    }
  }

  function toggleScope(scope: ProjectScope) {
    setSelectedScopes((current) => (current.includes(scope) ? current.filter((item) => item !== scope) : [...current, scope]));
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-iron-100 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-iron-950">Municipality Intelligence</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
            Build 26 standards checklist for cost-impacting municipal requirements, RFQ notes, estimating allowances, and bid review warnings.
          </p>
        </div>
      </div>

      <ProjectScopeNotice name={projectContext.projectName} />

      <form className="space-y-6" onSubmit={check}>
        <div className="rounded-md border border-iron-100 bg-white p-5">
          <h2 className="text-base font-semibold text-iron-950">Project Requirements</h2>
          <div className="mt-4 grid gap-4 lg:grid-cols-[320px_1fr]">
            <label className="grid gap-1 text-sm">
              <span className="font-medium text-iron-700">Municipality</span>
              <select value={municipality} onChange={(event) => setMunicipality(event.target.value)} className="rounded-md border border-iron-100 px-3 py-2">
                {municipalities.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
            </label>
            <div>
              <div className="text-sm font-medium text-iron-700">Scopes</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {scopes.map((scope) => (
                  <button
                    key={scope}
                    type="button"
                    onClick={() => toggleScope(scope)}
                    className={[
                      "rounded-md border px-3 py-2 text-sm font-medium",
                      selectedScopes.includes(scope) ? "border-iron-950 bg-iron-950 text-white" : "border-iron-100 bg-white text-iron-800",
                    ].join(" ")}
                  >
                    {scope}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {error ? <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}

        <button type="submit" disabled={isLoading} className="inline-flex items-center gap-2 rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white">
          {isLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <CheckSquare className="h-4 w-4" />}
          Check municipality requirements
        </button>
      </form>

      {result ? <MunicipalityResult result={result} /> : null}
    </section>
  );
}

function MunicipalityResult({ result }: { result: MunicipalityCheckResponse }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <SummaryCard label="Requirements" value={String(result.requirement_count)} />
        <SummaryCard label="High Impact" value={String(result.high_impact_count)} />
        <SummaryCard label="Scopes" value={result.project_scopes.join(", ") || "All"} />
      </div>

      {result.warnings.length ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <div className="flex items-center gap-2 font-semibold"><AlertTriangle className="h-4 w-4" />Warnings</div>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {result.warnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        </div>
      ) : null}

      <div className="space-y-4">
        {result.requirements.map((requirement) => (
          <div key={`${requirement.municipality}-${requirement.category}-${requirement.title}`} className="rounded-md border border-iron-100 bg-white p-5">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <div className="text-xs uppercase tracking-wide text-iron-500">{requirement.category}</div>
                <h3 className="mt-1 text-base font-semibold text-iron-950">{requirement.title}</h3>
                <p className="mt-2 text-sm leading-6 text-iron-500">{requirement.description}</p>
              </div>
              <span className={[
                "rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide",
                requirement.cost_impact === "high" ? "bg-red-100 text-red-700" : requirement.cost_impact === "medium" ? "bg-amber-100 text-amber-700" : "bg-iron-100 text-iron-700",
              ].join(" ")}>{requirement.cost_impact}</span>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <Note title="Estimating note" text={requirement.estimating_note} />
              <Note title="RFQ note" text={requirement.rfq_note ?? "No RFQ note."} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Note({ title, text }: { title: string; text: string }) {
  return <div className="rounded-md bg-iron-50 p-3"><div className="text-xs font-semibold uppercase tracking-wide text-iron-500">{title}</div><p className="mt-1 text-sm leading-6 text-iron-700">{text}</p></div>;
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md border border-iron-100 bg-white p-4"><div className="text-sm font-medium text-iron-500">{label}</div><div className="mt-2 text-xl font-semibold text-iron-950">{value}</div></div>;
}
