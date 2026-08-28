import { Activity, BookOpen, Calculator, CalendarDays, FileStack, FolderKanban, Plus, RefreshCw, RotateCcw, Search, ShieldCheck, Table2, Trash2, Users } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  AwardedProjectWorkspace,
  Project,
  ProjectCloseoutChecklist,
  ProjectCreatePayload,
  ProjectDashboard,
  ProjectLaunchDashboard,
  ProjectStartChecklist,
  ProjectStatus,
  projectStatuses,
  projectsApi,
} from "../api/projects";
import { financeApi, ProjectInvoicePackageReadiness, ProjectInvoicePackageResult } from "../api/finance";
import { CompletedWorkCostPanel } from "../components/CompletedWorkCostPanel";
import { useAuth } from "../contexts/AuthContext";
import { modulePathWithProjectContext, storeActiveProject, withProjectContext } from "../utils/projectContext";

const tabs = [
  "Overview",
  "Tender Info",
  "Documents",
  "Drawings",
  "RFQs",
  "Suppliers",
  "Quotes",
  "Estimate",
  "Schedule",
  "Municipality",
  "Bid Package",
  "Activity",
];

const releaseSmokeNamePattern = /^Release smoke (\d{8}-\d{6})$/;
const releaseSmokeProjectNumberPattern = /^SMOKE-(\d{8}-\d{6})$/;

function isReleaseSmokeProject(project: Project) {
  const nameMatch = releaseSmokeNamePattern.exec(project.name);
  const projectNumberMatch = releaseSmokeProjectNumberPattern.exec(project.project_number ?? "");
  return Boolean(nameMatch && projectNumberMatch && nameMatch[1] === projectNumberMatch[1]);
}

function filterProjects(projects: Project[], normalizedSearch: string, releaseSmokeOnly: boolean) {
  return projects.filter((project) => {
    const searchable = [project.project_number, project.name, project.municipality, label(project.status)]
      .filter(Boolean)
      .join(" ")
      .toLocaleLowerCase();
    const matchesSearch = !normalizedSearch || searchable.includes(normalizedSearch);
    const matchesReleaseSmoke = !releaseSmokeOnly || isReleaseSmokeProject(project);
    return matchesSearch && matchesReleaseSmoke;
  });
}

export function ProjectWorkspacePage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const isManagement = user?.role === "admin" || user?.role === "operations_manager";
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [dashboard, setDashboard] = useState<ProjectDashboard | null>(null);
  const [workspace, setWorkspace] = useState<AwardedProjectWorkspace | null>(null);
  const [launchDashboard, setLaunchDashboard] = useState<ProjectLaunchDashboard | null>(null);
  const [startChecklist, setStartChecklist] = useState<ProjectStartChecklist | null>(null);
  const [closeoutChecklist, setCloseoutChecklist] = useState<ProjectCloseoutChecklist | null>(null);
  const [invoicePackageReadiness, setInvoicePackageReadiness] = useState<ProjectInvoicePackageReadiness | null>(null);
  const [projectLoadWarning, setProjectLoadWarning] = useState<string | null>(null);
  const [savingChecklistCode, setSavingChecklistCode] = useState<string | null>(null);
  const [savingCloseoutCode, setSavingCloseoutCode] = useState<string | null>(null);
  const [initializingCloseout, setInitializingCloseout] = useState(false);
  const [dashboardByProjectId, setDashboardByProjectId] = useState<Record<string, ProjectDashboard>>({});
  const [statusFilter, setStatusFilter] = useState("");
  const [searchFilter, setSearchFilter] = useState("");
  const [smokeTestOnly, setSmokeTestOnly] = useState(false);
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [bulkDeleteResult, setBulkDeleteResult] = useState<string | null>(null);
  const [showTrash, setShowTrash] = useState(false);
  const [activeTab, setActiveTab] = useState("Overview");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setProjectLoadWarning(null);
    try {
      const list = await projectsApi.list(statusFilter, showTrash);
      const visibleProjects = showTrash ? list.items.filter((project) => project.deleted_at) : list.items;
      setProjects(visibleProjects);
      const summaries = await Promise.all(
        visibleProjects.filter((project) => !project.deleted_at).map(async (project) => [project.id, await projectsApi.dashboard(project.id)] as const),
      );
      setDashboardByProjectId(Object.fromEntries(summaries));
      if (projectId) {
        const detail = await projectsApi.detail(projectId);
        const summary = await projectsApi.dashboard(projectId);
        setSelectedProject(detail);
        setDashboard(summary);
        setWorkspace(null);
        setLaunchDashboard(null);
        setStartChecklist(null);
        setCloseoutChecklist(null);
        setInvoicePackageReadiness(null);

        const closeoutEligible = Boolean(
          detail.project_number && ["awarded", "construction", "completed"].includes(detail.status),
        );
        const [workspaceResult, checklistResult, launchResult, closeoutResult, invoicePackageResult] = await Promise.allSettled([
          detail.workspace_root ? projectsApi.workspace(projectId) : Promise.resolve(null),
          detail.workspace_root ? projectsApi.startChecklist(projectId) : Promise.resolve(null),
          detail.workspace_root && detail.status === "awarded"
            ? projectsApi.launchDashboard(projectId)
            : Promise.resolve(null),
          closeoutEligible ? projectsApi.closeoutChecklist(projectId) : Promise.resolve(null),
          isManagement && detail.status === "completed"
            ? financeApi.getProjectInvoicePackageReadiness(projectId)
            : Promise.resolve(null),
        ]);
        setWorkspace(workspaceResult.status === "fulfilled" ? workspaceResult.value : null);
        setStartChecklist(checklistResult.status === "fulfilled" ? checklistResult.value : null);
        setLaunchDashboard(launchResult.status === "fulfilled" ? launchResult.value : null);
        setCloseoutChecklist(closeoutResult.status === "fulfilled" ? closeoutResult.value : null);
        setInvoicePackageReadiness(invoicePackageResult.status === "fulfilled" ? invoicePackageResult.value : null);

        const unavailable = [
          detail.workspace_root && workspaceResult.status === "rejected" ? "workspace summary" : null,
          detail.workspace_root && checklistResult.status === "rejected" ? "start checklist" : null,
          detail.workspace_root && detail.status === "awarded" && launchResult.status === "rejected"
            ? "launch dashboard"
            : null,
          closeoutEligible && closeoutResult.status === "rejected" ? "closeout checklist" : null,
          isManagement && detail.status === "completed" && invoicePackageResult.status === "rejected"
            ? "draft invoice package readiness"
            : null,
        ].filter(Boolean);
        if (unavailable.length) {
          setProjectLoadWarning(
            `${detail.name} is selected, but its ${unavailable.join(", ")} could not be loaded. Available project controls remain usable.`,
          );
        }
      } else {
        setSelectedProject(null);
        setDashboard(null);
        setWorkspace(null);
        setLaunchDashboard(null);
        setStartChecklist(null);
        setCloseoutChecklist(null);
        setInvoicePackageReadiness(null);
      }
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to load projects");
    } finally {
      setIsLoading(false);
    }
  }, [isManagement, projectId, showTrash, statusFilter]);

  useEffect(() => {
    // This effect synchronizes the project workspace with route and filter changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (selectedProject) storeActiveProject(selectedProject);
  }, [selectedProject]);

  async function createProject(payload: ProjectCreatePayload) {
    const created = await projectsApi.create(payload);
    navigate(`/projects/${created.id}`);
  }

  async function updateStatus(status: ProjectStatus) {
    if (!selectedProject) return;
    setError(null);
    try {
      await projectsApi.update(selectedProject.id, { status });
      await refresh();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to update project status");
    }
  }

  async function refreshInvoicePackageReadiness() {
    if (!selectedProject || selectedProject.status !== "completed" || !isManagement) return;
    const readiness = await financeApi.getProjectInvoicePackageReadiness(selectedProject.id);
    setInvoicePackageReadiness(readiness);
  }

  async function archiveProject() {
    if (!selectedProject) return;
    await projectsApi.archive(selectedProject.id);
    await refresh();
  }

  async function deleteProject() {
    if (!selectedProject || !isAdmin) return;
    const confirmation = window.prompt(`Type the exact project name to move it to trash:\n\n${selectedProject.name}`);
    if (confirmation === null) return;
    await projectsApi.delete(selectedProject.id, confirmation);
    navigate("/projects");
  }

  async function restoreProject(project: Project) {
    if (!isAdmin) return;
    await projectsApi.restore(project.id);
    await refresh();
  }

  async function moveFilteredReleaseSmokeProjectsToTrash() {
    if (!isAdmin || bulkDeleting) return;
    setBulkDeleting(true);
    setBulkDeleteResult(null);
    setError(null);
    let moved = 0;
    let failingProject: Project | null = null;
    try {
      const currentList = await projectsApi.list(statusFilter, false);
      const currentProjects = currentList.items.filter((project) => !project.deleted_at);
      const currentCandidates = filterProjects(currentProjects, normalizedSearch, true);
      setProjects(currentProjects);

      if (currentCandidates.length === 0) {
        setBulkDeleteResult("No active release smoke projects remain in the current filter.");
        return;
      }

      const confirmed = window.confirm(
        `Move ${currentCandidates.length} filtered release smoke ${currentCandidates.length === 1 ? "project" : "projects"} to recoverable Trash?\n\nOnly exact Release smoke records with matching SMOKE job numbers will be changed.`,
      );
      if (!confirmed) return;

      for (const project of currentCandidates) {
        failingProject = project;
        await projectsApi.delete(project.id, project.name);
        moved += 1;
      }
      await refresh();
      setBulkDeleteResult(
        `${moved} release smoke ${moved === 1 ? "project" : "projects"} moved to Trash. They can be restored by an administrator.`,
      );
    } catch (currentError) {
      await refresh();
      setError(
        `${moved} release smoke ${moved === 1 ? "project" : "projects"} moved to Trash before cleanup stopped${
          failingProject ? ` at ${failingProject.name} (${failingProject.project_number ?? "no project number"})` : ""
        }. ${
          currentError instanceof Error ? currentError.message : "Unable to complete smoke/test cleanup."
        }`,
      );
    } finally {
      setBulkDeleting(false);
    }
  }

  async function updateStartChecklistItem(code: string, completed: boolean) {
    if (!selectedProject || savingChecklistCode) return;
    setSavingChecklistCode(code);
    setError(null);
    try {
      const updated = await projectsApi.updateStartChecklistItem(selectedProject.id, code, completed);
      setStartChecklist(updated);
      setLaunchDashboard((current) =>
        current
          ? {
              ...current,
              mobilization_status: updated.status,
              checklist_completed_count: updated.completed_count,
              checklist_total_count: updated.total_count,
              next_incomplete_control: updated.items.find((item) => !item.completed) ?? null,
            }
          : current,
      );
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to update the job start checklist");
    } finally {
      setSavingChecklistCode(null);
    }
  }

  async function initializeCloseoutChecklist() {
    if (!selectedProject || !isManagement || initializingCloseout) return;
    setInitializingCloseout(true);
    setError(null);
    try {
      setCloseoutChecklist(await projectsApi.initializeCloseoutChecklist(selectedProject.id));
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to initialize project closeout controls");
    } finally {
      setInitializingCloseout(false);
    }
  }

  async function updateCloseoutChecklistItem(code: string, completed: boolean, evidence?: string | null) {
    if (!selectedProject || !isManagement || savingCloseoutCode) return;
    setSavingCloseoutCode(code);
    setError(null);
    try {
      setCloseoutChecklist(
        await projectsApi.updateCloseoutChecklistItem(selectedProject.id, code, completed, evidence),
      );
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to update the project closeout checklist");
    } finally {
      setSavingCloseoutCode(null);
    }
  }

  const normalizedSearch = searchFilter.trim().toLocaleLowerCase();
  const filteredProjects = filterProjects(projects, normalizedSearch, smokeTestOnly);

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-iron-100 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-iron-950">Project Workspace</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
            Command center for live bids and awarded jobs: tender intake, documents, RFQs, suppliers, quotes, estimate, risk, and delivery records.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          className="inline-flex items-center gap-2 rounded-md border border-iron-100 bg-white px-3 py-2 text-sm font-medium text-iron-800"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {error ? <Notice tone="error" message={error} /> : null}
      {projectLoadWarning ? <Notice tone="error" message={projectLoadWarning} /> : null}
      {bulkDeleteResult ? <Notice tone="neutral" message={bulkDeleteResult} /> : null}
      {isLoading ? <Notice tone="neutral" message="Loading projects..." /> : null}

      <div
        className={[
          "grid gap-6 xl:grid-cols-[420px_1fr]",
          projectId ? "[@media(pointer:coarse)]:!grid-cols-1" : "",
        ]
          .filter(Boolean)
          .join(" ")}
      >
        <div
          className={[
            "min-w-0 space-y-6",
            projectId ? "order-last xl:order-none [@media(pointer:coarse)]:!order-last" : "",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          <ProjectFilters
            status={statusFilter}
            search={searchFilter}
            smokeTestOnly={smokeTestOnly}
            onStatusChange={setStatusFilter}
            onSearchChange={setSearchFilter}
            onSmokeTestOnlyChange={setSmokeTestOnly}
          />
          {isAdmin && smokeTestOnly && !showTrash && filteredProjects.length > 0 ? (
            <button
              type="button"
              disabled={bulkDeleting}
              onClick={() => void moveFilteredReleaseSmokeProjectsToTrash()}
              className="inline-flex min-h-11 items-center gap-2 rounded-md border border-red-200 bg-white px-3 py-2 text-sm font-semibold text-red-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Trash2 className="h-4 w-4" />
              {bulkDeleting
                ? "Moving release smoke projects to Trash..."
                : `Move ${filteredProjects.length} release smoke projects to Trash`}
            </button>
          ) : null}
          {isAdmin ? (
            <button
              type="button"
              onClick={() => setShowTrash((value) => !value)}
              className="inline-flex items-center gap-2 rounded-md border border-iron-100 bg-white px-3 py-2 text-sm font-semibold text-iron-800"
            >
              {showTrash ? <FolderKanban className="h-4 w-4" /> : <Trash2 className="h-4 w-4" />}
              {showTrash ? "Back to projects" : "View trash"}
            </button>
          ) : null}
          <CreateProjectForm onSubmit={(payload) => void createProject(payload)} />
          <ProjectList projects={filteredProjects} selectedId={projectId} dashboards={dashboardByProjectId} showTrash={showTrash} onRestore={(project) => void restoreProject(project)} />
        </div>
        {selectedProject && dashboard ? (
          <ProjectDetail
            project={selectedProject}
            dashboard={dashboard}
            workspace={workspace}
            launchDashboard={launchDashboard}
            startChecklist={startChecklist}
            closeoutChecklist={closeoutChecklist}
            invoicePackageReadiness={invoicePackageReadiness}
            savingChecklistCode={savingChecklistCode}
            savingCloseoutCode={savingCloseoutCode}
            initializingCloseout={initializingCloseout}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            onStatusChange={(value) => void updateStatus(value)}
            onArchive={() => void archiveProject()}
            onDelete={() => void deleteProject()}
            canDelete={isAdmin}
            canManageCloseout={isManagement}
            onStartChecklistChange={(code, completed) => void updateStartChecklistItem(code, completed)}
            onInitializeCloseout={() => void initializeCloseoutChecklist()}
            onCloseoutChecklistChange={(code, completed, evidence) => void updateCloseoutChecklistItem(code, completed, evidence)}
            onInvoicePackageGenerated={() => refreshInvoicePackageReadiness()}
          />
        ) : (
          <div className="rounded-md border border-iron-100 bg-white p-6">
            <h2 className="text-base font-semibold text-iron-950">No project selected</h2>
            <p className="mt-2 text-sm leading-6 text-iron-500">
              Create or select a project to open the workspace dashboard.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

function ProjectFilters({
  status,
  search,
  smokeTestOnly,
  onStatusChange,
  onSearchChange,
  onSmokeTestOnlyChange,
}: {
  status: string;
  search: string;
  smokeTestOnly: boolean;
  onStatusChange: (value: string) => void;
  onSearchChange: (value: string) => void;
  onSmokeTestOnlyChange: (value: boolean) => void;
}) {
  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <h2 className="text-base font-semibold text-iron-950">Project Filters</h2>
      <label className="relative mt-4 block">
        <span className="sr-only">Search projects</span>
        <Search aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-iron-500" />
        <input
          type="search"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          className="w-full rounded-md border border-iron-100 py-2 pl-9 pr-3 text-sm"
          placeholder="Search job #, name, municipality, or status"
        />
      </label>
      <select
        aria-label="Project status filter"
        value={status}
        onChange={(event) => onStatusChange(event.target.value)}
        className="mt-3 w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
      >
        <option value="">All statuses</option>
        {projectStatuses.map((item) => (
          <option key={item} value={item}>
            {label(item)}
          </option>
        ))}
      </select>
      <label className="mt-3 flex min-h-11 cursor-pointer items-center gap-3 rounded-md border border-iron-100 px-3 py-2 text-sm font-semibold text-iron-800">
        <input
          type="checkbox"
          checked={smokeTestOnly}
          onChange={(event) => onSmokeTestOnlyChange(event.target.checked)}
          className="h-4 w-4 rounded border-iron-200"
        />
        Release smoke projects only
      </label>
    </div>
  );
}

function CreateProjectForm({ onSubmit }: { onSubmit: (payload: ProjectCreatePayload) => void }) {
  const [name, setName] = useState("");
  const [municipality, setMunicipality] = useState("");
  const [bidDueDate, setBidDueDate] = useState("");
  const [status, setStatus] = useState<ProjectStatus>("opportunity");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) return;
    onSubmit({
      name: name.trim(),
      municipality: municipality.trim() || undefined,
      bid_due_date: bidDueDate || undefined,
      status,
    });
    setName("");
    setMunicipality("");
    setBidDueDate("");
  }

  return (
    <form className="rounded-md border border-iron-100 bg-white p-5" onSubmit={handleSubmit}>
      <div className="mb-4 flex items-center gap-2">
        <Plus className="h-5 w-5 text-signal-green" />
        <h2 className="text-base font-semibold text-iron-950">Create Project</h2>
      </div>
      <div className="space-y-3">
        <Field label="Project name">
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            placeholder="King George Utility Upgrade"
          />
        </Field>
        <Field label="Municipality">
          <input
            value={municipality}
            onChange={(event) => setMunicipality(event.target.value)}
            className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            placeholder="Surrey"
          />
        </Field>
        <Field label="Bid due date">
          <input
            type="date"
            value={bidDueDate}
            onChange={(event) => setBidDueDate(event.target.value)}
            className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
          />
        </Field>
        <Field label="Project stage">
          <select
            aria-label="Project stage"
            value={status}
            onChange={(event) => setStatus(event.target.value as ProjectStatus)}
            className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
          >
            <option value="opportunity">Opportunity</option>
            <option value="tendering">Tendering</option>
            <option value="awarded">Awarded</option>
          </select>
        </Field>
        {status === "awarded" ? (
          <div role="status" className="rounded-md border border-brand-gold/40 bg-brand-gold/5 p-3 text-sm text-iron-700">
            IHOS will generate the next unique job number when this awarded project is created.
          </div>
        ) : null}
      </div>
      <button
        type="submit"
        className="mt-5 inline-flex items-center gap-2 rounded-md bg-iron-950 px-3 py-2 text-sm font-semibold text-white"
      >
        <FolderKanban className="h-4 w-4" />
        {status === "awarded" ? "Create awarded job" : "Create"}
      </button>
    </form>
  );
}

function ProjectList({
  projects,
  selectedId,
  dashboards,
  showTrash,
  onRestore,
}: {
  projects: Project[];
  selectedId: string | undefined;
  dashboards: Record<string, ProjectDashboard>;
  showTrash: boolean;
  onRestore: (project: Project) => void;
}) {
  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <h2 className="text-base font-semibold text-iron-950">Projects</h2>
      <div aria-label="Projects table" role="region" tabIndex={0} className="mt-4 overflow-x-auto">
        <table className="w-full border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-iron-100 text-xs uppercase tracking-wide text-iron-500">
              <th className="py-2 pr-4">Job #</th>
              <th className="py-2 pr-4">Name</th>
              <th className="py-2 pr-4">Municipality</th>
              <th className="py-2 pr-4">Status</th>
              <th className="py-2 pr-4">Bid Due</th>
              <th className="py-2 pr-4">Ready</th>
              <th className="py-2 pr-4">Docs</th>
              {showTrash ? <th className="py-2 pr-4">Action</th> : null}
            </tr>
          </thead>
          <tbody>
            {projects.map((project) => {
              const summary = dashboards[project.id];
              return (
                <tr
                  key={project.id}
                  className={["border-b border-iron-100 last:border-b-0", selectedId === project.id ? "bg-iron-50" : ""].join(
                    " ",
                  )}
                >
                  <td className="py-3 pr-4 font-semibold text-iron-800">{project.project_number ?? "Pending award"}</td>
                  <td className="py-3 pr-4 font-medium text-iron-950">{showTrash ? project.name : <Link to={`/projects/${project.id}`}>{project.name}</Link>}</td>
                  <td className="py-3 pr-4 text-iron-800">{project.municipality ?? "Unassigned"}</td>
                  <td className="py-3 pr-4 text-iron-800">{label(project.status)}</td>
                  <td className="py-3 pr-4 text-iron-800">{project.bid_due_date ?? "Not set"}</td>
                  <td className="py-3 pr-4 text-iron-800">{summary ? `${summary.readiness_percentage}%` : "Loading"}</td>
                  <td className="py-3 pr-4 text-iron-800">{summary ? summary.document_count : "Loading"}</td>
                  {showTrash ? (
                    <td className="py-3 pr-4">
                      <button type="button" onClick={() => onRestore(project)} className="inline-flex items-center gap-2 rounded-md border border-iron-100 px-3 py-2 font-semibold text-iron-800">
                        <RotateCcw className="h-4 w-4" /> Restore
                      </button>
                    </td>
                  ) : null}
                </tr>
              );
            })}
            {projects.length === 0 ? (
              <tr>
                <td className="py-3 text-iron-500" colSpan={showTrash ? 8 : 7}>
                  {showTrash ? "Trash is empty." : "No projects found."}
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ProjectDetail({
  project,
  dashboard,
  workspace,
  launchDashboard,
  startChecklist,
  closeoutChecklist,
  invoicePackageReadiness,
  savingChecklistCode,
  savingCloseoutCode,
  initializingCloseout,
  activeTab,
  onTabChange,
  onStatusChange,
  onArchive,
  onDelete,
  canDelete,
  canManageCloseout,
  onStartChecklistChange,
  onInitializeCloseout,
  onCloseoutChecklistChange,
  onInvoicePackageGenerated,
}: {
  project: Project;
  dashboard: ProjectDashboard;
  workspace: AwardedProjectWorkspace | null;
  launchDashboard: ProjectLaunchDashboard | null;
  startChecklist: ProjectStartChecklist | null;
  closeoutChecklist: ProjectCloseoutChecklist | null;
  invoicePackageReadiness: ProjectInvoicePackageReadiness | null;
  savingChecklistCode: string | null;
  savingCloseoutCode: string | null;
  initializingCloseout: boolean;
  activeTab: string;
  onTabChange: (tab: string) => void;
  onStatusChange: (status: ProjectStatus) => void;
  onArchive: () => void;
  onDelete: () => void;
  canDelete: boolean;
  canManageCloseout: boolean;
  onStartChecklistChange: (code: string, completed: boolean) => void;
  onInitializeCloseout: () => void;
  onCloseoutChecklistChange: (code: string, completed: boolean, evidence?: string | null) => void;
  onInvoicePackageGenerated: () => Promise<void>;
}) {
  return (
    <div className="space-y-6">
      <div className="rounded-md border border-iron-100 bg-white p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="text-xs uppercase tracking-wide text-iron-500">{project.project_number ?? "Project"}</div>
            <h2 className="mt-1 text-2xl font-semibold text-iron-950">{project.name}</h2>
            <p className="mt-2 text-sm text-iron-500">
              {project.client_owner ?? "No client set"} - {project.municipality ?? "No municipality"}
            </p>
          </div>
          <div className="flex gap-2">
            <select
              aria-label="Project status"
              value={project.status}
              disabled={project.status === "completed" && !canManageCloseout}
              onChange={(event) => onStatusChange(event.target.value as ProjectStatus)}
              className="rounded-md border border-iron-100 bg-white px-3 py-2 text-sm disabled:bg-iron-50 disabled:text-iron-500"
            >
              {projectStatuses.map((item) => (
                <option key={item} value={item} disabled={item === "completed" && !canManageCloseout}>
                  {label(item)}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={onArchive}
              className="rounded-md border border-iron-100 px-3 py-2 text-sm font-semibold text-iron-800"
            >
              Archive
            </button>
            {canDelete ? (
              <button type="button" onClick={onDelete} className="inline-flex items-center gap-2 rounded-md border border-red-200 px-3 py-2 text-sm font-semibold text-red-700">
                <Trash2 className="h-4 w-4" /> Delete
              </button>
            ) : null}
          </div>
        </div>
      </div>

      {workspace ? <AwardedWorkspaceCard workspace={workspace} /> : null}
      {launchDashboard ? <ProjectLaunchDashboardCard dashboard={launchDashboard} project={project} /> : null}
      {startChecklist ? (
        <ProjectStartChecklistCard
          checklist={startChecklist}
          savingCode={savingChecklistCode}
          onChange={onStartChecklistChange}
        />
      ) : null}
      {closeoutChecklist ? (
        <ProjectCloseoutChecklistCard
          checklist={closeoutChecklist}
          savingCode={savingCloseoutCode}
          canManage={canManageCloseout}
          projectCompleted={project.status === "completed"}
          onChange={onCloseoutChecklistChange}
        />
      ) : project.project_number && canManageCloseout && ["awarded", "construction", "completed"].includes(project.status) ? (
        <CloseoutInitializationCard
          initializing={initializingCloseout}
          onInitialize={onInitializeCloseout}
        />
      ) : null}
      {project.status === "completed" && canManageCloseout && invoicePackageReadiness ? (
        <ProjectInvoicePackageCard
          readiness={invoicePackageReadiness}
          onGenerated={onInvoicePackageGenerated}
        />
      ) : null}
      {canManageCloseout ? <CompletedWorkCostPanel projectId={project.id} /> : null}
      <DashboardWidgets dashboard={dashboard} project={project} />
      <CommandCenter project={project} dashboard={dashboard} />

      <div className="rounded-md border border-iron-100 bg-white">
        <div className="flex overflow-x-auto border-b border-iron-100">
          {tabs.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => onTabChange(tab)}
              className={["whitespace-nowrap px-4 py-3 text-sm font-medium", activeTab === tab ? "text-iron-950" : "text-iron-500"].join(
                " ",
              )}
            >
              {tab}
            </button>
          ))}
        </div>
        <div className="p-5">
          <TabBody tab={activeTab} project={project} dashboard={dashboard} />
        </div>
      </div>
    </div>
  );
}

function ProjectLaunchDashboardCard({
  dashboard,
  project,
}: {
  dashboard: ProjectLaunchDashboard;
  project: Project;
}) {
  const safetyRecordCount = Object.values(dashboard.safety_record_counts).reduce((total, count) => total + count, 0);
  const ready = dashboard.mobilization_status === "ready";
  const actions = [
    { label: "Estimate", href: "/estimating", description: "Confirm the priced estimate and handoff." },
    { label: "Budget", href: "/finance", description: "Establish the baseline budget and cost codes." },
    { label: "Purchase orders", href: "/request-po", description: "Prepare and route project PO requests." },
    { label: "Safety", href: "/safety-operations", description: "Create project-specific safety records." },
    { label: "Documents", href: "/documents", description: "Register current award and construction files." },
  ];
  return (
    <section aria-label="Job launch dashboard" className="rounded-md border border-brand-gold/40 bg-white p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-brand-gold" aria-hidden="true" />
            <h2 className="text-base font-semibold text-iron-950">Job launch dashboard</h2>
          </div>
          <p className="mt-2 text-sm leading-6 text-iron-500">
            One view of the records needed to move {dashboard.job_number} from award into controlled mobilization.
          </p>
        </div>
        <span
          className={[
            "w-fit rounded-md px-3 py-2 text-xs font-semibold",
            ready ? "bg-signal-green/10 text-signal-green" : "bg-brand-gold/10 text-iron-800",
          ].join(" ")}
        >
          {ready ? "Mobilization controls ready" : "Mobilization controls not ready"}
        </span>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <LaunchMetric
          label="Start checklist"
          value={`${dashboard.checklist_completed_count} of ${dashboard.checklist_total_count}`}
          detail={dashboard.next_incomplete_control ? `Next: ${dashboard.next_incomplete_control.label}` : "All controls confirmed."}
        />
        <LaunchMetric
          label="Priced estimate"
          value={dashboard.priced_estimate_available ? "Available" : "Missing"}
          detail={`${dashboard.estimate_workspace_count} estimate workspace${dashboard.estimate_workspace_count === 1 ? "" : "s"}`}
        />
        <LaunchMetric
          label="Baseline budget"
          value={formatCurrency(dashboard.baseline_budget_total)}
          detail={`${dashboard.budget_entry_count} active budget entr${dashboard.budget_entry_count === 1 ? "y" : "ies"}`}
        />
        <LaunchMetric
          label="PO requests"
          value={String(dashboard.po_request_count)}
          detail={`${dashboard.pending_po_request_count} awaiting approval`}
        />
        <LaunchMetric
          label="Safety records"
          value={String(safetyRecordCount)}
          detail="Project-linked records only"
        />
        <LaunchMetric
          label="Safety launch"
          value={label(dashboard.safety_release_status)}
          detail={`${dashboard.safety_requirement_count} record requirement(s) · folder ${label(dashboard.safety_folder_status).toLowerCase()} · portal ${label(dashboard.portal_access_status).toLowerCase()} (${dashboard.portal_assignment_count} assignment(s))`}
        />
        <LaunchMetric
          label="Field production"
          value={label(dashboard.production_posting_status)}
          detail={`${dashboard.production_post_count} of ${dashboard.daily_sheet_count} daily sheet(s) posted · latest ${label(dashboard.latest_daily_sheet_status).toLowerCase()} · folder ${label(dashboard.field_production_folder_status).toLowerCase()}${dashboard.production_blockers.length ? ` · blockers: ${dashboard.production_blockers.map(label).join(", ")}` : ""}`}
        />
        <LaunchMetric label="Documents" value={String(dashboard.document_count)} detail="Project-linked records only" />
        <LaunchMetric
          label="Award pricing baseline"
          value={dashboard.award_baseline_source ?? "Not initialized"}
          detail={dashboard.award_baseline_source ? `${formatCurrency(dashboard.award_pricing_subtotal)} customer pricing · ${dashboard.uncoded_award_line_count} line(s) need cost codes` : "Accept a controlled customer quote to initialize."}
        />
        <LaunchMetric
          label="Procurement plan"
          value={label(dashboard.procurement_plan_status)}
          detail={`${dashboard.procurement_requirement_count} draft requirement(s) · no automatic commitment`}
        />
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {actions.map((action) => (
          <Link
            key={action.label}
            to={withProjectContext(action.href, project)}
            className="rounded-md border border-iron-100 p-3 hover:bg-iron-50"
          >
            <span className="block text-sm font-semibold text-iron-950">{action.label}</span>
            <span className="mt-1 block text-xs leading-5 text-iron-500">{action.description}</span>
          </Link>
        ))}
      </div>
      <p className="mt-4 text-xs leading-5 text-iron-500">
        Estimate, budget, PO, safety, and document totals are launch indicators. Only the project-start checklist determines the
        mobilization-ready status; no approval is inferred from a record count.
      </p>
    </section>
  );
}

function LaunchMetric({ label: itemLabel, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-md border border-iron-100 bg-iron-50 p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-iron-500">{itemLabel}</div>
      <div className="mt-2 text-xl font-semibold text-iron-950">{value}</div>
      <p className="mt-1 text-xs leading-5 text-iron-500">{detail}</p>
    </div>
  );
}

function AwardedWorkspaceCard({ workspace }: { workspace: AwardedProjectWorkspace }) {
  const topLevelFolders = workspace.entries.filter((entry) => {
    if (entry.kind !== "folder") return false;
    const relativePath = entry.path.slice(workspace.root_folder.length + 1);
    return !relativePath.includes("/");
  });
  return (
    <section aria-label="Awarded project workspace" className="rounded-md border border-brand-gold/40 bg-white p-5">
      <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <FolderKanban className="h-5 w-5 text-brand-gold" />
            <h2 className="text-base font-semibold text-iron-950">Awarded job workspace prepared</h2>
          </div>
          <p className="mt-2 text-sm leading-6 text-iron-500">
            IHOS prepared the standard project structure once for job {workspace.job_number}. Later project edits will not rename it.
          </p>
        </div>
        <div className="rounded-md bg-iron-50 px-3 py-2 text-xs font-semibold text-iron-800">{workspace.entries.length} entries</div>
      </div>
      <div className="mt-4 rounded-md border border-iron-100 bg-iron-50 px-3 py-2 font-mono text-xs text-iron-800">
        {workspace.root_folder}
      </div>
      <ul className="mt-4 grid gap-2 md:grid-cols-2" aria-label="Prepared workspace checklist">
        {topLevelFolders.map((entry) => (
          <li key={entry.path} className="flex items-center gap-2 text-sm text-iron-700">
            <ShieldCheck className="h-4 w-4 shrink-0 text-signal-green" aria-hidden="true" />
            <span>{entry.path.slice(workspace.root_folder.length + 1)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function ProjectStartChecklistCard({
  checklist,
  savingCode,
  onChange,
}: {
  checklist: ProjectStartChecklist;
  savingCode: string | null;
  onChange: (code: string, completed: boolean) => void;
}) {
  const ready = checklist.status === "ready";
  return (
    <section aria-label="Awarded job start checklist" className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-brand-gold" aria-hidden="true" />
            <h2 className="text-base font-semibold text-iron-950">Awarded job start checklist</h2>
          </div>
          <p className="mt-2 text-sm leading-6 text-iron-500">
            Confirm the standard project-start controls by selecting each completed item.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={[
              "rounded-md px-3 py-2 text-xs font-semibold",
              ready ? "bg-signal-green/10 text-signal-green" : "bg-brand-gold/10 text-iron-800",
            ].join(" ")}
          >
            {ready ? "Ready" : "Not ready"}
          </span>
          <span className="text-sm font-semibold text-iron-800">
            {checklist.completed_count} of {checklist.total_count}
          </span>
        </div>
      </div>
      <div className="mt-5 grid gap-3 md:grid-cols-2">
        {checklist.items.map((item) => (
          <label
            key={item.code}
            className="flex min-h-12 cursor-pointer items-start gap-3 rounded-md border border-iron-100 p-3 hover:bg-iron-50"
          >
            <input
              type="checkbox"
              checked={item.completed}
              disabled={savingCode !== null}
              onChange={(event) => onChange(item.code, event.target.checked)}
              className="mt-0.5 h-5 w-5 shrink-0 accent-signal-green"
            />
            <span>
              <span className="block text-xs font-semibold uppercase tracking-wide text-iron-500">{item.category}</span>
              <span className="mt-1 block text-sm leading-5 text-iron-800">{item.label}</span>
              {item.changed_by && item.changed_at ? (
                <span className="mt-1 block text-xs text-iron-500">
                  Recorded by {item.changed_by} at <time dateTime={item.changed_at}>{new Date(item.changed_at).toLocaleString()}</time>
                </span>
              ) : null}
            </span>
          </label>
        ))}
      </div>
      <p className="mt-4 text-xs leading-5 text-iron-500">
        A checked item records management confirmation only. It does not replace source documents, permits, contract approval,
        engineering approval, or project-specific safety evidence.
      </p>
    </section>
  );
}

function CloseoutInitializationCard({
  initializing,
  onInitialize,
}: {
  initializing: boolean;
  onInitialize: () => void;
}) {
  return (
    <section aria-label="Project closeout controls" className="rounded-md border border-brand-gold/40 bg-white p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-base font-semibold text-iron-950">Project closeout controls</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
            This legacy job has no closeout checklist yet. Initialize the standard controls before attempting project completion.
          </p>
        </div>
        <button
          type="button"
          disabled={initializing}
          onClick={onInitialize}
          className="min-h-11 rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {initializing ? "Initializing…" : "Initialize closeout controls"}
        </button>
      </div>
    </section>
  );
}

function ProjectCloseoutChecklistCard({
  checklist,
  savingCode,
  canManage,
  projectCompleted,
  onChange,
}: {
  checklist: ProjectCloseoutChecklist;
  savingCode: string | null;
  canManage: boolean;
  projectCompleted: boolean;
  onChange: (code: string, completed: boolean, evidence?: string | null) => void;
}) {
  const ready = checklist.status === "ready";
  return (
    <section aria-label="Project closeout checklist" className="rounded-md border border-brand-gold/40 bg-white p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-brand-gold" aria-hidden="true" />
            <h2 className="text-base font-semibold text-iron-950">Project closeout checklist</h2>
          </div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
            Record the source document, email, inspection, invoice, or other evidence for every closeout control.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={[
              "rounded-md px-3 py-2 text-xs font-semibold",
              ready ? "bg-signal-green/10 text-signal-green" : "bg-brand-gold/10 text-iron-800",
            ].join(" ")}
          >
            {ready ? "Ready for management completion" : "Not ready"}
          </span>
          <span className="text-sm font-semibold text-iron-800">
            {checklist.completed_count} of {checklist.total_count}
          </span>
        </div>
      </div>
      <div className="mt-5 grid gap-3 lg:grid-cols-2">
        {checklist.items.map((item) => (
          <CloseoutChecklistItemControl
            key={`${item.code}-${item.completed}-${item.changed_at ?? "new"}`}
            item={item}
            saving={savingCode !== null}
            canManage={canManage}
            projectCompleted={projectCompleted}
            onChange={onChange}
          />
        ))}
      </div>
      <p className="mt-4 text-xs leading-5 text-iron-500">
        Checklist readiness does not issue an invoice, release holdback, prove payment, replace source documents, or infer client,
        consultant, regulatory, or contract acceptance. Management must still select the project completion status separately.
      </p>
    </section>
  );
}

function ProjectInvoicePackageCard({
  readiness,
  onGenerated,
}: {
  readiness: ProjectInvoicePackageReadiness;
  onGenerated: () => Promise<void>;
}) {
  const initialGroup = readiness.groups.find((group) => group.ready && !group.existing_invoice_id) ?? readiness.groups[0];
  const [sourceImportKey, setSourceImportKey] = useState(initialGroup?.source_import_key ?? "");
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [customerName, setCustomerName] = useState(readiness.customer_reference ?? "");
  const [customerAddress, setCustomerAddress] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");
  const [invoiceDate, setInvoiceDate] = useState(todayIsoDate());
  const [dueDate, setDueDate] = useState(addDaysIso(todayIsoDate(), 30));
  const [terms, setTerms] = useState("Net 30");
  const [gstRate, setGstRate] = useState("5.00");
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<ProjectInvoicePackageResult | null>(null);
  const [packageError, setPackageError] = useState<string | null>(null);
  const selectedGroup = readiness.groups.find((group) => group.source_import_key === sourceImportKey) ?? null;
  const canGenerate = Boolean(
    readiness.ready
      && selectedGroup?.ready
      && !selectedGroup.existing_invoice_id
      && invoiceNumber.trim()
      && customerName.trim()
      && customerAddress.trim()
      && invoiceDate
      && dueDate
      && terms.trim()
      && gstRate.trim(),
  );

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canGenerate || saving) return;
    setSaving(true);
    setPackageError(null);
    try {
      const generated = await financeApi.generateProjectInvoicePackage(readiness.project_id, {
        source_import_key: sourceImportKey,
        invoice_number: invoiceNumber.trim(),
        customer_name: customerName.trim(),
        customer_address: customerAddress.trim(),
        customer_phone: customerPhone.trim() || null,
        invoice_date: invoiceDate,
        due_date: dueDate,
        terms: terms.trim(),
        gst_rate: gstRate.trim(),
      });
      setResult(generated);
      await onGenerated();
    } catch (currentError) {
      setPackageError(currentError instanceof Error ? currentError.message : "Unable to generate draft invoice package");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section aria-label="Draft invoice package" className="rounded-md border border-brand-gold/40 bg-white p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <FileStack className="h-5 w-5 text-brand-gold" aria-hidden="true" />
            <h2 className="text-base font-semibold text-iron-950">Draft invoice package</h2>
          </div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
            Select one exact completed-work source group, confirm the billing identity, and generate a traceable draft for review.
          </p>
        </div>
        <span className={[
          "w-fit rounded-md px-3 py-2 text-xs font-semibold",
          readiness.ready ? "bg-signal-green/10 text-signal-green" : "bg-brand-gold/10 text-iron-800",
        ].join(" ")}>
          {readiness.ready ? "Source package ready" : "Source package blocked"}
        </span>
      </div>

      {readiness.blockers.length ? (
        <ul className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          {readiness.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}
        </ul>
      ) : null}

      {readiness.groups.length ? (
        <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.8fr)]">
          <div>
            <Field label="Completed-work source group">
              <select
                aria-label="Completed-work source group"
                value={sourceImportKey}
                onChange={(event) => {
                  setSourceImportKey(event.target.value);
                  setResult(null);
                  setPackageError(null);
                }}
                className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
              >
                {readiness.groups.map((group) => (
                  <option key={group.source_import_key} value={group.source_import_key}>
                    {group.source_invoice_number ?? group.source_import_key} · {group.line_count} line(s) · {formatCurrency(Number(group.subtotal))}{group.existing_invoice_id ? " · draft exists" : group.ready ? " · ready" : " · blocked"}
                  </option>
                ))}
              </select>
            </Field>
            {selectedGroup ? (
              <div className="mt-4 rounded-md border border-iron-100">
                <div className="grid gap-2 border-b border-iron-100 bg-iron-50 p-3 text-xs text-iron-600 sm:grid-cols-3">
                  <span>Source: {selectedGroup.source_invoice_number ?? "No source invoice number"}</span>
                  <span>Date: {selectedGroup.source_invoice_date ?? "Not recorded"}</span>
                  <span>Total: {formatCurrency(Number(selectedGroup.subtotal))}</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-iron-100 text-xs uppercase tracking-wide text-iron-500">
                        <th className="p-3">Completed work</th>
                        <th className="p-3">Quantity</th>
                        <th className="p-3">Rate</th>
                        <th className="p-3">Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedGroup.lines.map((line) => (
                        <tr key={line.id} className="border-b border-iron-100 last:border-b-0">
                          <td className="p-3 text-iron-900">{line.description}</td>
                          <td className="p-3 text-iron-700">{line.quantity} {line.unit}</td>
                          <td className="p-3 text-iron-700">{formatCurrency(Number(line.billable_rate))}</td>
                          <td className="p-3 font-semibold text-iron-900">{formatCurrency(Number(line.billable_amount))}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {selectedGroup.blockers.length ? (
                  <ul className="border-t border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900">
                    {selectedGroup.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}
                  </ul>
                ) : null}
              </div>
            ) : null}
          </div>

          {selectedGroup?.existing_invoice_id ? (
            <div className="rounded-md border border-signal-green/30 bg-signal-green/5 p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-signal-green">Existing invoice package</div>
              <p className="mt-2 text-lg font-semibold text-iron-950">{selectedGroup.existing_invoice_number}</p>
              <p className="mt-1 text-sm text-iron-600">Status: {label(selectedGroup.existing_invoice_status ?? "draft")}</p>
              <a
                href={financeApi.customerInvoicePdfUrl(selectedGroup.existing_invoice_id)}
                target="_blank"
                rel="noreferrer"
                className="mt-4 inline-flex min-h-11 items-center rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white"
              >
                Open draft PDF
              </a>
            </div>
          ) : (
            <form onSubmit={generate} className="rounded-md border border-iron-100 p-4">
              <h3 className="text-sm font-semibold text-iron-950">Confirm draft billing details</h3>
              <p className="mt-1 text-xs leading-5 text-iron-500">
                Project and source-work values are locked to verified records. Confirm all customer billing fields before generating.
              </p>
              <div className="mt-4 space-y-3">
                <Field label="Invoice number">
                  <input aria-label="Invoice number" required maxLength={80} value={invoiceNumber} onChange={(event) => setInvoiceNumber(event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" />
                </Field>
                <Field label="Customer legal / billing name">
                  <input aria-label="Customer legal / billing name" required maxLength={255} value={customerName} onChange={(event) => setCustomerName(event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" />
                </Field>
                <Field label="Customer billing address">
                  <textarea aria-label="Customer billing address" required maxLength={500} rows={2} value={customerAddress} onChange={(event) => setCustomerAddress(event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" />
                </Field>
                <Field label="Customer phone (if known)">
                  <input aria-label="Customer phone (if known)" maxLength={40} value={customerPhone} onChange={(event) => setCustomerPhone(event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" />
                </Field>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Invoice date">
                    <input aria-label="Invoice date" required type="date" value={invoiceDate} onChange={(event) => setInvoiceDate(event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" />
                  </Field>
                  <Field label="Due date">
                    <input aria-label="Due date" required type="date" min={invoiceDate} value={dueDate} onChange={(event) => setDueDate(event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" />
                  </Field>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Terms">
                    <input aria-label="Terms" required maxLength={80} value={terms} onChange={(event) => setTerms(event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" />
                  </Field>
                  <Field label="GST rate (%)">
                    <input aria-label="GST rate (%)" required inputMode="decimal" maxLength={20} value={gstRate} onChange={(event) => setGstRate(event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" />
                  </Field>
                </div>
              </div>
              {packageError ? <p role="alert" className="mt-3 text-sm text-red-700">{packageError}</p> : null}
              {result ? (
                <div role="status" className="mt-3 rounded-md border border-signal-green/30 bg-signal-green/5 p-3 text-sm text-iron-800">
                  Draft {result.invoice.invoice_number} generated. It remains unapproved and unissued.
                </div>
              ) : null}
              <button type="submit" disabled={!canGenerate || saving} className="mt-4 min-h-11 w-full rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
                {saving ? "Generating draft…" : "Generate traceable draft"}
              </button>
            </form>
          )}
        </div>
      ) : (
        <p className="mt-4 rounded-md border border-iron-100 bg-iron-50 p-4 text-sm text-iron-600">
          No completed-work source groups are available for this project.
        </p>
      )}
      <p className="mt-4 text-xs leading-5 text-iron-500">
        Generated packages are drafts only. This action does not approve, issue, send, export, mark paid, release holdback, or infer customer acceptance.
      </p>
    </section>
  );
}

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}

function addDaysIso(value: string, days: number) {
  const date = new Date(`${value}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function CloseoutChecklistItemControl({
  item,
  saving,
  canManage,
  projectCompleted,
  onChange,
}: {
  item: ProjectCloseoutChecklist["items"][number];
  saving: boolean;
  canManage: boolean;
  projectCompleted: boolean;
  onChange: (code: string, completed: boolean, evidence?: string | null) => void;
}) {
  const [evidence, setEvidence] = useState(item.evidence ?? "");
  const normalizedEvidence = evidence.trim();
  const evidenceChanged = normalizedEvidence !== (item.evidence ?? "");
  return (
    <article className="rounded-md border border-iron-100 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-iron-500">{item.category}</div>
          <p className="mt-1 text-sm leading-5 text-iron-800">{item.label}</p>
        </div>
        <span className={item.completed ? "text-xs font-semibold text-signal-green" : "text-xs font-semibold text-iron-500"}>
          {item.completed ? "Complete" : "Open"}
        </span>
      </div>
      <label className="mt-3 block text-xs font-semibold text-iron-700">
        Evidence
        <textarea
          aria-label={`Evidence for ${item.label}`}
          value={evidence}
          disabled={!canManage || saving}
          onChange={(event) => setEvidence(event.target.value)}
          rows={2}
          maxLength={2000}
          placeholder="Document, email, inspection, invoice, or record reference"
          className="mt-1 w-full rounded-md border border-iron-100 px-3 py-2 text-sm font-normal text-iron-800 disabled:bg-iron-50"
        />
      </label>
      {item.changed_by && item.changed_at ? (
        <p className="mt-2 text-xs text-iron-500">
          Recorded by {item.changed_by} at <time dateTime={item.changed_at}>{new Date(item.changed_at).toLocaleString()}</time>
        </p>
      ) : null}
      {canManage ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {item.completed ? (
            <>
              <button
                type="button"
                disabled={saving || !normalizedEvidence || !evidenceChanged}
                onClick={() => onChange(item.code, true, normalizedEvidence)}
                className="min-h-10 rounded-md border border-iron-200 px-3 py-2 text-xs font-semibold text-iron-800 disabled:opacity-50"
              >
                Update evidence
              </button>
              <button
                type="button"
                disabled={saving || projectCompleted}
                onClick={() => onChange(item.code, false, null)}
                className="min-h-10 rounded-md border border-iron-200 px-3 py-2 text-xs font-semibold text-iron-700 disabled:opacity-50"
              >
                Reopen control
              </button>
            </>
          ) : (
            <button
              type="button"
              disabled={saving || !normalizedEvidence}
              onClick={() => onChange(item.code, true, normalizedEvidence)}
              className="min-h-10 rounded-md bg-iron-950 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
            >
              Confirm complete
            </button>
          )}
        </div>
      ) : null}
    </article>
  );
}

function DashboardWidgets({ dashboard, project }: { dashboard: ProjectDashboard; project: Project }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <Widget icon={<Activity className="h-4 w-4" />} label="RFQ readiness" value={`${dashboard.readiness_percentage}%`} />
      <Widget icon={<FileStack className="h-4 w-4" />} label="Documents" value={String(dashboard.document_count)} />
      <Widget icon={<Users className="h-4 w-4" />} label="Supplier coverage" value={String(dashboard.supplier_count)} />
      <Widget icon={<CalendarDays className="h-4 w-4" />} label="Bid due" value={project.bid_due_date ?? "Not set"} />
      <Widget icon={<FileStack className="h-4 w-4" />} label="Drawings" value={String(dashboard.drawing_count)} />
      <Widget icon={<Activity className="h-4 w-4" />} label="RFQs" value={String(dashboard.rfq_count)} />
      <Widget icon={<Activity className="h-4 w-4" />} label="Bid status" value={label(dashboard.bid_status)} />
      <Widget icon={<CalendarDays className="h-4 w-4" />} label="Tender close" value={project.tender_closing_date ?? "Not set"} />
    </div>
  );
}

function CommandCenter({ project, dashboard }: { project: Project; dashboard: ProjectDashboard }) {
  const nextStep = getNextStep(project, dashboard);
  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-base font-semibold text-iron-950">Command Center</h2>
          <p className="mt-1 text-sm leading-6 text-iron-500">Next practical move: {nextStep}</p>
        </div>
        <div className="text-sm font-semibold text-iron-950">Readiness {dashboard.readiness_percentage}%</div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <ActionCard icon={<FileStack className="h-4 w-4" />} label="RFQs" description="Create packages and draft supplier requests." href={withProjectContext("/rfq-builder", project)} />
        <ActionCard icon={<BookOpen className="h-4 w-4" />} label="Documents" description="Register drawings, specs, addenda, and RFQ files." href={withProjectContext("/documents", project)} />
        <ActionCard icon={<Users className="h-4 w-4" />} label="Suppliers" description="Find or add suppliers for the project scope." href={withProjectContext("/suppliers", project)} />
        <ActionCard icon={<Table2 className="h-4 w-4" />} label="Quotes" description="Compare supplier pricing and selection reasons." href={withProjectContext("/quotes", project)} />
        <ActionCard icon={<Calculator className="h-4 w-4" />} label="Estimate" description="Build price, markups, risk, and workbook export." href={withProjectContext("/estimating", project)} />
        <ActionCard icon={<ShieldCheck className="h-4 w-4" />} label="Municipality" description="Track standards, permits, inspections, and risks." href={withProjectContext("/municipality-intelligence", project)} />
        <ActionCard icon={<CalendarDays className="h-4 w-4" />} label="Schedule" description="Track bid due date, quote deadlines, and work windows." href={`/projects/${project.id}`} />
        <ActionCard icon={<FolderKanban className="h-4 w-4" />} label="Bid Package" description="Assemble final scope, estimate, assumptions, and exclusions." href={withProjectContext("/bid-package", project)} />
      </div>
    </div>
  );
}

function ActionCard({ icon, label: itemLabel, description, href }: { icon: React.ReactNode; label: string; description: string; href: string }) {
  return (
    <Link to={href} className="rounded-md border border-iron-100 p-4 hover:bg-iron-50">
      <div className="flex items-center gap-2 text-sm font-semibold text-iron-950">
        {icon}
        {itemLabel}
      </div>
      <p className="mt-2 text-xs leading-5 text-iron-500">{description}</p>
    </Link>
  );
}

function Widget({ icon, label: itemLabel, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-md border border-iron-100 bg-white p-4">
      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-iron-500">
        {icon}
        {itemLabel}
      </div>
      <div className="mt-2 text-2xl font-semibold text-iron-950">{value}</div>
    </div>
  );
}

function TabBody({ tab, project, dashboard }: { tab: string; project: Project; dashboard: ProjectDashboard }) {
  const details: Record<string, { summary: string; actions: { label: string; href: string }[] }> = {
    Overview: {
      summary: project.notes ?? "Project overview notes will live here. Use this tab to capture bid decisions and assumptions.",
      actions: [
        { label: "Open estimate", href: "/estimating" },
        { label: "Open RFQs", href: "/rfq-builder" },
      ],
    },
    "Tender Info": {
      summary: `Owner: ${project.client_owner ?? "Not set"}. Municipality: ${project.municipality ?? "Not set"}. Tender close: ${project.tender_closing_date ?? "Not set"}.`,
      actions: [{ label: "Open tender tracker", href: "/tenders" }],
    },
    Documents: {
      summary: `${dashboard.document_count} documents linked to this project. Register drawings, specs, addenda, and RFQ files before pricing.`,
      actions: [{ label: "Open document library", href: "/documents" }],
    },
    Drawings: {
      summary: `${dashboard.drawing_count} drawings linked to this project. Future drawing intelligence will extract quantities and conflicts from here.`,
      actions: [{ label: "Open drawing intelligence", href: "/drawing-intelligence" }],
    },
    RFQs: {
      summary: `${dashboard.rfq_count} RFQ packages linked to this project. Build package scopes and track supplier readiness here.`,
      actions: [{ label: "Open RFQ builder", href: "/rfq-builder" }],
    },
    Suppliers: {
      summary: `${dashboard.supplier_count} suppliers linked to this project. Add missing suppliers before sending RFQs.`,
      actions: [{ label: "Open supplier database", href: "/suppliers" }],
    },
    Quotes: {
      summary: "Compare received quotes by line item and preserve selection reasons when not using the lowest price.",
      actions: [{ label: "Open quote comparison", href: "/quotes" }],
    },
    Estimate: {
      summary: "Build the bid price using line items, production defaults, risk, contingency, bonding, insurance, overhead, profit, and workbook export.",
      actions: [{ label: "Open estimating", href: "/estimating" }],
    },
    Schedule: {
      summary: `Bid due: ${project.bid_due_date ?? "Not set"}. Track quote deadlines, expected award, and construction window here as the schedule module matures.`,
      actions: [{ label: "Review project list", href: "/projects" }],
    },
    Municipality: {
      summary: `Municipality: ${project.municipality ?? "Not set"}. Track supplementary standards, permit requirements, inspections, approved materials, restoration, and testing requirements here.`,
      actions: [{ label: "Open municipality intelligence", href: "/municipality-intelligence" }],
    },
    "Bid Package": {
      summary: "Final package should include scope, price, schedule, assumptions, exclusions, addenda review, bonds/insurance, and RFQ quote backup.",
      actions: [
        { label: "Generate bid package", href: "/bid-package" },
        { label: "Open estimating", href: "/estimating" },
      ],
    },
    Activity: {
      summary: "Activity stream is reserved for future audit events, status changes, quote receipts, RFQ sends, and bid decisions.",
      actions: [],
    },
  };
  const content = details[tab] ?? details.Overview;
  return (
    <div className="space-y-4">
      <p className="text-sm leading-6 text-iron-500">{content.summary}</p>
      {content.actions.length ? (
        <div className="flex flex-wrap gap-2">
          {content.actions.map((action) => (
            <Link key={action.label} to={modulePathWithProjectContext(action.href, { projectId: project.id, projectName: project.name })} className="rounded-md border border-iron-100 px-3 py-2 text-sm font-semibold text-iron-800">
              {action.label}
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function getNextStep(project: Project, dashboard: ProjectDashboard) {
  if (!project.bid_due_date) return "set the bid due date so quote and estimate deadlines are anchored.";
  if (dashboard.document_count === 0) return "register the drawings, specs, and addenda in the document library.";
  if (dashboard.supplier_count === 0) return "add supplier coverage for the main scopes.";
  if (dashboard.rfq_count === 0) return "create RFQ packages for pipe, aggregates, asphalt, concrete, testing, and specialty scopes.";
  if (dashboard.readiness_percentage < 80) return "finish RFQ readiness items before final pricing.";
  return "build the estimate, compare quotes, and assemble the bid package.";
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-CA", {
    style: "currency",
    currency: "CAD",
    maximumFractionDigits: 0,
  }).format(value);
}

function Field({ label: itemLabel, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-iron-800">{itemLabel}</span>
      {children}
    </label>
  );
}

function Notice({ tone, message }: { tone: "neutral" | "error"; message: string }) {
  const className = tone === "error" ? "border-signal-red bg-white text-signal-red" : "border-iron-100 bg-white text-iron-500";
  return <div className={`rounded-md border px-4 py-3 text-sm ${className}`}>{message}</div>;
}

function label(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
