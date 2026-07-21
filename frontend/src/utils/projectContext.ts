import { Project } from "../api/projects";

export type ProjectContext = {
  projectId: string | null;
  projectName: string | null;
};

const ACTIVE_PROJECT_KEY = "ihos:active-project";

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

export function storeActiveProject(project: Pick<Project, "id" | "name">): void {
  window.localStorage.setItem(ACTIVE_PROJECT_KEY, JSON.stringify({ projectId: project.id, projectName: project.name }));
}

export function readActiveProject(): ProjectContext {
  try {
    const value = JSON.parse(window.localStorage.getItem(ACTIVE_PROJECT_KEY) ?? "null") as ProjectContext | null;
    return value?.projectId ? value : { projectId: null, projectName: null };
  } catch {
    return { projectId: null, projectName: null };
  }
}

export function readEffectiveProjectContext(search: string): ProjectContext {
  const routed = readProjectContext(search);
  return hasProjectContext(routed) ? routed : readActiveProject();
}

export function modulePathWithProjectContext(path: string, context: ProjectContext): string {
  if (!context.projectId || !context.projectName) return path;
  if (path === "/projects") return `/projects/${context.projectId}`;
  const projectAwarePaths = new Set([
    "/mvp-workflow",
    "/project-operations",
    "/document-operations",
    "/rfq-builder",
    "/rfq-automation",
    "/bid-package",
    "/documents",
    "/estimating",
    "/drawing-intelligence",
    "/quantity-takeoff",
    "/municipality-intelligence",
    "/quotes",
  ]);
  return projectAwarePaths.has(path)
    ? withProjectContext(path, { id: context.projectId, name: context.projectName })
    : path;
}
