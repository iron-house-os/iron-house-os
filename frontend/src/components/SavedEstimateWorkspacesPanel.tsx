import { useState } from "react";

import { estimateWorkspaceApi, EstimateWorkspaceList } from "../api/estimateWorkspace";

type Props = {
  projectId?: string | null;
};

export function SavedEstimateWorkspacesPanel({ projectId }: Props) {
  const [workspaces, setWorkspaces] = useState<EstimateWorkspaceList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function loadWorkspaces() {
    if (!projectId) {
      setError("Open a project before loading estimate workspaces.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      setWorkspaces(await estimateWorkspaceApi.listForProject(projectId));
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to load estimate workspaces");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-base font-semibold text-iron-950">Saved Estimate Workspaces</h2>
          <p className="mt-1 text-sm text-iron-500">Review estimate/bid workspace records attached to this project.</p>
        </div>
        <button type="button" onClick={loadWorkspaces} disabled={isLoading} className="rounded-md border border-iron-100 px-4 py-2 text-sm font-semibold text-iron-800">
          {isLoading ? "Loading..." : "Load estimates"}
        </button>
      </div>
      {error ? <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
      {workspaces ? <div className="mt-4 space-y-2 text-sm text-iron-700">{workspaces.items.map((item) => <div key={item.id} className="rounded-md border border-iron-100 p-3">{item.status} - {item.total_amount ? `$${item.total_amount.toLocaleString()}` : "No total"} - {item.summary_text ?? item.id}</div>)}{workspaces.total === 0 ? <div>No saved estimate workspaces yet.</div> : null}</div> : null}
    </div>
  );
}
