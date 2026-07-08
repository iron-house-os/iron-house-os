import { useState } from "react";

import { RFQAutomationInputItem, RFQLinkageResponse, rfqLinkageApi } from "../api/rfqLinkage";

type Props = {
  projectId?: string | null;
  projectName?: string | null;
  municipality?: string | null;
  sourceItems: RFQAutomationInputItem[];
};

export function RFQLinkagePanel({ projectId, projectName, municipality, sourceItems }: Props) {
  const [result, setResult] = useState<RFQLinkageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function buildDrafts() {
    setIsLoading(true);
    setError(null);
    try {
      setResult(await rfqLinkageApi.buildDrafts({ project_id: projectId, project_name: projectName, municipality, source_items: sourceItems, include_default_civil_scopes: true }));
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to build RFQ linkage");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-base font-semibold text-iron-950">RFQ Linkage</h2>
          <p className="mt-1 text-sm text-iron-500">Convert takeoff or estimate scope into RFQ package drafts with target supplier categories and required documents.</p>
        </div>
        <button type="button" onClick={buildDrafts} disabled={isLoading} className="rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white">
          {isLoading ? "Building..." : "Build RFQ drafts"}
        </button>
      </div>
      {error ? <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
      {result ? <div className="mt-4 space-y-3">{result.packages.map((pkg) => <div key={pkg.title} className="rounded-md border border-iron-100 p-3 text-sm text-iron-700"><div className="font-semibold text-iron-950">{pkg.title}</div><p className="mt-1">{pkg.scope_summary}</p><div className="mt-2 text-xs uppercase tracking-wide text-iron-500">Priority {pkg.priority}</div></div>)}</div> : null}
    </div>
  );
}
