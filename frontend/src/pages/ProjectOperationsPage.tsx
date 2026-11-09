import { useState } from "react";
import { useLocation } from "react-router-dom";

import { ActiveProjectSelector } from "../components/ActiveProjectSelector";
import { ProjectReadinessPanel } from "../components/ProjectReadinessPanel";
import { SavedEstimateWorkspacesPanel } from "../components/SavedEstimateWorkspacesPanel";
import { SavedTakeoffsPanel } from "../components/SavedTakeoffsPanel";
import { readEffectiveProjectContext } from "../utils/projectContext";

export function ProjectOperationsPage() {
  const location = useLocation();
  const context = readEffectiveProjectContext(location.search);
  const [projectId, setProjectId] = useState(context.projectId ?? "");

  return (
    <section className="space-y-6">
      <div className="border-b border-iron-100 pb-6">
        <h1 className="text-3xl font-semibold text-iron-950">Project Operations</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
          Build 65 project operations page for loading saved takeoffs, estimate workspaces, and readiness by project ID.
        </p>
      </div>

      <ActiveProjectSelector value={projectId} onChange={(project) => setProjectId(project?.id ?? "")} />

      <ProjectReadinessPanel projectId={projectId || null} />
      <SavedTakeoffsPanel projectId={projectId || null} />
      <SavedEstimateWorkspacesPanel projectId={projectId || null} />
    </section>
  );
}
