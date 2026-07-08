import { useState } from "react";

import { projectReadinessApi, ProjectReadinessResponse } from "../api/projectReadiness";

type Props = {
  projectId?: string | null;
};

export function ProjectReadinessPanel({ projectId }: Props) {
  const [readiness, setReadiness] = useState<ProjectReadinessResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function loadReadiness() {
    if (!projectId) {
      setError("Save or open a project before checking readiness.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      setReadiness(await projectReadinessApi.get(projectId));
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to load project readiness");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-base font-semibold text-iron-950">Project Readiness</h2>
          <p className="mt-1 text-sm text-iron-500">Checks whether the project has the minimum documents, takeoffs, estimate workspace, and RFQs needed for bid review.</p>
        </div>
        <button type="button" onClick={loadReadiness} disabled={isLoading} className="rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white">
          {isLoading ? "Checking..." : "Check readiness"}
        </button>
      </div>

      {error ? <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}

      {readiness ? (
        <div className="mt-5 space-y-4">
          <div className="rounded-md border border-iron-100 p-4">
            <div className="text-sm font-medium text-iron-500">Readiness score</div>
            <div className="mt-1 text-3xl font-semibold text-iron-950">{readiness.readiness_score}%</div>
            <div className="mt-1 text-sm uppercase tracking-wide text-iron-500">{readiness.status}</div>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {readiness.items.map((item) => (
              <div key={item.label} className="rounded-md border border-iron-100 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm font-semibold text-iron-950">{item.label}</div>
                  <div className="text-xs uppercase tracking-wide text-iron-500">{item.status}</div>
                </div>
                <p className="mt-2 text-sm text-iron-600">{item.detail}</p>
              </div>
            ))}
          </div>
          <List title="Blockers" items={readiness.blockers} />
          <List title="Next actions" items={readiness.next_actions} />
        </div>
      ) : null}
    </div>
  );
}

function List({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return <div className="rounded-md border border-iron-100 p-3 text-sm text-iron-700"><div className="font-semibold text-iron-950">{title}</div><ul className="mt-2 list-disc space-y-1 pl-5">{items.map((item) => <li key={item}>{item}</li>)}</ul></div>;
}
