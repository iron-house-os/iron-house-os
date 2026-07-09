import { useState } from "react";

import { ProjectReadinessPanel } from "../components/ProjectReadinessPanel";
import { SavedEstimateWorkspacesPanel } from "../components/SavedEstimateWorkspacesPanel";
import { SavedTakeoffsPanel } from "../components/SavedTakeoffsPanel";

export function ProjectOperationsPage() {
  const [projectId, setProjectId] = useState("");

  return (
    <section className="space-y-6">
      <div className="border-b border-iron-100 pb-6">
        <h1 className="text-3xl font-semibold text-iron-950">Project Operations</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
          Build 65 project operations page for loading saved takeoffs, estimate workspaces, and readiness by project ID.
        </p>
      </div>

      <div className="rounded-md border border-iron-100 bg-white p-5">
        <label className="grid gap-1 text-sm">
          <span className="font-medium text-iron-700">Project ID</span>
          <input value={projectId} onChange={(event) => setProjectId(event.target.value)} className="rounded-md border border-iron-100 px-3 py-2" placeholder="Paste project UUID" />
        </label>
      </div>

      <ProjectReadinessPanel projectId={projectId || null} />
      <SavedTakeoffsPanel projectId={projectId || null} />
      <SavedEstimateWorkspacesPanel projectId={projectId || null} />
    </section>
  );
}
