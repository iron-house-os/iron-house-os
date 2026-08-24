import { Activity, BookOpen, Calculator, CalendarDays, FileStack, FolderKanban, Plus, RefreshCw, RotateCcw, Search, ShieldCheck, Table2, Trash2, Users } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  AwardedProjectWorkspace,
  Project,
  ProjectCreatePayload,
  ProjectDashboard,
  ProjectLaunchDashboard,
  ProjectStartChecklist,
  ProjectStatus,
  projectStatuses,
  projectsApi,
} from "../api/projects";
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

export function ProjectWorkspacePage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [dashboard, setDashboard] = useState<ProjectDashboard | null>(null);
  const [workspace, setWorkspace] = useState<AwardedProjectWorkspace | null>(null);
  const [launchDashboard, setLaunchDashboard] = useState<ProjectLaunchDashboard | null>(null);
  const [startChecklist, setStartChecklist] = useState<ProjectStartChecklist | null>(null);
  const [projectLoadWarning, setProjectLoadWarning] = useState<string | null>(null);
  const [savingChecklistCode, setSavingChecklistCode] = useState<string | null>(null);
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

        if (detail.workspace_root) {
          const [workspaceResult, checklistResult, launchResult] = await Promise.allSettled([
            projectsApi.workspace(projectId),
            projectsApi.startChecklist(projectId),
            projectsApi.launchDashboard(projectId),
          ]);
          setWorkspace(workspaceResult.status === "fulfilled" ? workspaceResult.value : null);
          setStartChecklist(checklistResult.status === "fulfilled" ? checklistResult.value : null);
          setLaunchDashboard(launchResult.status === "fulfilled" ? launchResult.value : null);

          const unavailable = [
            workspaceResult.status === "rejected" ? "workspace summary" : null,
            checklistResult.status === "rejected" ? "start checklist" : null,
            launchResult.status === "rejected" ? "launch dashboard" : null,
          ].filter(Boolean);
          if (unavailable.length) {
            setProjectLoadWarning(
              `${detail.name} is selected, but its ${unavailable.join(", ")} could not be loaded. Available project controls remain usable.`,
            );
          }
        }
      } else {
        setSelectedProject(null);
        setDashboard(null);
        setWorkspace(null);
        setLaunchDashboard(null);
        setStartChecklist(null);
      }
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to load projects");
    } finally {
      setIsLoading(false);
    }
  }, [projectId, showTrash, statusFilter]);

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
    await projectsApi.update(selectedProject.id, { status });
    await refresh();
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

  async function moveFilteredSmokeTestsToTrash(filteredProjects: Project[]) {
    if (!isAdmin || bulkDeleting || filteredProjects.length === 0) return;
    const confirmed = window.confirm(
      `Move all ${filteredProjects.length} filtered smoke/test projects to recoverable Trash?\n\nNo other projects will be changed.`,
    );
    if (!confirmed) return;
    setBulkDeleting(true);
    setBulkDeleteResult(null);
    setError(null);
    let moved = 0;
    try {
      for (const project of filteredProjects) {
        await projectsApi.delete(project.id, project.name);
        moved += 1;
      }
      setBulkDeleteResult(`${moved} smoke/test projects moved to Trash. They can be restored by an administrator.`);
    } catch (currentError) {
      setError(
        `${moved} projects moved to Trash before cleanup stopped. ${
          currentError instanceof Error ? currentError.message : "Unable to complete smoke/test cleanup."
        }`,
      );
    } finally {
      await refresh();
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

  const normalizedSearch = searchFilter.trim().toLocaleLowerCase();
  const smokeTestMarker = /(?:^|[^a-z0-9])(smoke|test)(?:[^a-z0-9]|$)/i;
  const filteredProjects = projects.filter((project) => {
    const searchable = [project.project_number, project.name, project.municipality, label(project.status)]
      .filter(Boolean)
      .join(" ")
      .toLocaleLowerCase();
    const matchesSearch = !normalizedSearch || searchable.includes(normalizedSearch);
    const matchesSmokeTest = !smokeTestOnly || smokeTestMarker.test(`${project.project_number ?? ""} ${project.name}`);
    return matchesSearch && matchesSmokeTest;
  });

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

      <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
        <div className="min-w-0 space-y-6">
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
              onClick={() => void moveFilteredSmokeTestsToTrash(filteredProjects)}
              className="inline-flex min-h-11 items-center gap-2 rounded-md border border-red-200 bg-white px-3 py-2 text-sm font-semibold text-red-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Trash2 className="h-4 w-4" />
              {bulkDeleting
                ? "Moving smoke/test projects to Trash..."
                : `Move ${filteredProjects.length} filtered smoke/test projects to Trash`}
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
            savingChecklistCode={savingChecklistCode}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            onStatusChange={(value) => void updateStatus(value)}
            onArchive={() => void archiveProject()}
            onDelete={() => void deleteProject()}
            canDelete={isAdmin}
            onStartChecklistChange={(code, completed) => void updateStartChecklistItem(code, completed)}
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
        Smoke/test projects only
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
  savingChecklistCode,
  activeTab,
  onTabChange,
  onStatusChange,
  onArchive,
  onDelete,
  canDelete,
  onStartChecklistChange,
}: {
  project: Project;
  dashboard: ProjectDashboard;
  workspace: AwardedProjectWorkspace | null;
  launchDashboard: ProjectLaunchDashboard | null;
  startChecklist: ProjectStartChecklist | null;
  savingChecklistCode: string | null;
  activeTab: string;
  onTabChange: (tab: string) => void;
  onStatusChange: (status: ProjectStatus) => void;
  onArchive: () => void;
  onDelete: () => void;
  canDelete: boolean;
  onStartChecklistChange: (code: string, completed: boolean) => void;
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
              value={project.status}
              onChange={(event) => onStatusChange(event.target.value as ProjectStatus)}
              className="rounded-md border border-iron-100 bg-white px-3 py-2 text-sm"
            >
              {projectStatuses.map((item) => (
                <option key={item} value={item}>
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
