import { Project } from "../api/projects";

export type ProjectContext = {
  projectId: string | null;
  projectName: string | null;
};

export function buildProjectContextParams(project: Pick<Project, "id" | "name">): string {
  const params = new URLSearchParams({
    projectId: project.id,
    projectName: project.name,
  });
  return params.toString();
}

export function withProjectContext(path: string, project: Pick<Project, "id" | "name">): string {
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}${buildProjectContextParams(project)}`;
}

export function readProjectContext(search: string): ProjectContext {
  const params = new URLSearchParams(search);
  return {
    projectId: params.get("projectId"),
    projectName: params.get("projectName"),
  };
}

export function hasProjectContext(context: ProjectContext): boolean {
  return Boolean(context.projectId || context.projectName);
}
