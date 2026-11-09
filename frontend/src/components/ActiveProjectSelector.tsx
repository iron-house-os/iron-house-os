import { useEffect, useState } from "react";

import { Project, projectsApi } from "../api/projects";
import { storeActiveProject } from "../utils/projectContext";

export function ActiveProjectSelector({ value, onChange }: { value: string; onChange: (project: Project | null) => void }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    projectsApi.list().then((result) => {
      if (cancelled) return;
      const ordered = [...result.items]
        .filter((project) => project.status !== "archived")
        .sort((left, right) => right.updated_at.localeCompare(left.updated_at));
      setProjects(ordered);
      const selected = ordered.find((project) => project.id === value) ?? ordered[0] ?? null;
      if (selected) {
        storeActiveProject(selected);
        onChange(selected);
      }
    }).catch((currentError) => {
      if (!cancelled) setError(currentError instanceof Error ? currentError.message : "Unable to load projects");
    }).finally(() => {
      if (!cancelled) setIsLoading(false);
    });
    return () => { cancelled = true; };
  }, []);

  function select(projectId: string) {
    const project = projects.find((candidate) => candidate.id === projectId) ?? null;
    if (project) storeActiveProject(project);
    onChange(project);
  }

  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <label className="grid gap-1 text-sm">
        <span className="font-medium text-iron-700">Active project</span>
        <select aria-label="Active project" value={value} onChange={(event) => select(event.target.value)} disabled={isLoading} className="rounded-md border border-iron-100 px-3 py-2">
          <option value="">{isLoading ? "Loading projects..." : "Select a project"}</option>
          {projects.map((project) => <option key={project.id} value={project.id}>{project.name}{project.project_number ? ` — ${project.project_number}` : ""}</option>)}
        </select>
      </label>
      {error ? <p role="alert" className="mt-2 text-sm text-red-700">{error}</p> : null}
      {!isLoading && !projects.length ? <p className="mt-2 text-sm text-iron-500">Create a project first in Project Workspace.</p> : null}
    </div>
  );
}
