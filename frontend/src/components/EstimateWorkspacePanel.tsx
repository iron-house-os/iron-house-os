import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { customerQuotesApi } from "../api/customerQuotes";
import { estimateWorkspaceApi, EstimateWorkspaceRead } from "../api/estimateWorkspace";
import { EstimateCreate, EstimateSummary } from "../api/estimates";

type Props = {
  projectId?: string | null;
  estimate: EstimateCreate;
  summary?: EstimateSummary | null;
};

export function EstimateWorkspacePanel({ projectId, estimate, summary }: Props) {
  const navigate = useNavigate();
  const [saved, setSaved] = useState<EstimateWorkspaceRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isCreatingQuote, setIsCreatingQuote] = useState(false);

  async function persistWorkspace() {
    if (!projectId) throw new Error("Open a project before saving an estimate workspace.");
    const workspace = await estimateWorkspaceApi.save({ project_id: projectId, status: "draft", estimate, summary });
    setSaved(workspace);
    return workspace;
  }

  async function saveWorkspace() {
    setIsSaving(true);
    setError(null);
    try {
      await persistWorkspace();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to save estimate workspace");
    } finally {
      setIsSaving(false);
    }
  }

  async function createQuoteDraft() {
    if (!summary) {
      setError("Calculate the estimate before creating a customer quote draft.");
      return;
    }
    setIsCreatingQuote(true);
    setError(null);
    try {
      const workspace = await persistWorkspace();
      const quote = await customerQuotesApi.fromEstimate(workspace.id);
      navigate(`/customer-quotes?quoteId=${encodeURIComponent(quote.id)}&action=edit`);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to create customer quote draft");
    } finally {
      setIsCreatingQuote(false);
    }
  }

  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-base font-semibold text-iron-950">Estimate Workspace</h2>
          <p className="mt-1 text-sm text-iron-500">Save the active estimate against the project so it can be reopened and included in readiness checks.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={saveWorkspace} disabled={isSaving || isCreatingQuote} className="rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white disabled:bg-iron-300">
            {isSaving ? "Saving..." : "Save workspace"}
          </button>
          <button type="button" onClick={createQuoteDraft} disabled={!summary || isSaving || isCreatingQuote} className="rounded-md border border-brand-gold bg-white px-4 py-2 text-sm font-semibold text-iron-950 disabled:border-iron-100 disabled:text-iron-300">
            {isCreatingQuote ? "Creating..." : "Create quote draft"}
          </button>
        </div>
      </div>
      {error ? <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
      {saved ? <div className="mt-4 rounded-md border border-iron-100 p-3 text-sm text-iron-700">Saved estimate workspace: {saved.summary_text ?? saved.id}</div> : null}
    </div>
  );
}
