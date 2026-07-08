import { useState } from "react";

import { estimateWorkspaceApi, EstimateWorkspaceRead } from "../api/estimateWorkspace";
import { EstimateCreate, EstimateSummary } from "../api/estimates";

type Props = {
  projectId?: string | null;
  estimate: EstimateCreate;
  summary?: EstimateSummary | null;
};

export function EstimateWorkspacePanel({ projectId, estimate, summary }: Props) {
  const [saved, setSaved] = useState<EstimateWorkspaceRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  async function saveWorkspace() {
    if (!projectId) {
      setError("Open a project before saving an estimate workspace.");
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      setSaved(await estimateWorkspaceApi.save({ project_id: projectId, status: "draft", estimate, summary }));
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to save estimate workspace");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-base font-semibold text-iron-950">Estimate Workspace</h2>
          <p className="mt-1 text-sm text-iron-500">Save the active estimate against the project so it can be reopened and included in readiness checks.</p>
        </div>
        <button type="button" onClick={saveWorkspace} disabled={isSaving} className="rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white">
          {isSaving ? "Saving..." : "Save workspace"}
        </button>
      </div>
      {error ? <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
      {saved ? <div className="mt-4 rounded-md border border-iron-100 p-3 text-sm text-iron-700">Saved estimate workspace: {saved.summary_text ?? saved.id}</div> : null}
    </div>
  );
}
