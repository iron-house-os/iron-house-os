import { Activity, CalendarDays, FileStack, FolderKanban, Plus, RefreshCw } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  Project,
  ProjectCreatePayload,
  ProjectDashboard,
  ProjectStatus,
  projectStatuses,
  projectsApi,
} from "../api/projects";

const tabs = ["Overview", "RFQs", "Documents", "Suppliers", "Drawings", "Estimating", "Activity"];

export function ProjectWorkspacePage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [dashboard, setDashboard] = useState<ProjectDashboard | null>(null);
  const [dashboardByProjectId, setDashboardByProjectId] = useState<Record<string, ProjectDashboard>>({});
  const [statusFilter, setStatusFilter] = useState("");
  const [activeTab, setActiveTab] = useState("Overview");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const list = await projectsApi.list(statusFilter);
      setProjects(list.items);
      const summaries = await Promise.all(
        list.items.map(async (project) => [project.id, await projectsApi.dashboard(project.id)] as const),
      );
      setDashboardByProjectId(Object.fromEntries(summaries));
      if (projectId) {
        const [detail, summary] = await Promise.all([
          projectsApi.detail(projectId),
          projectsApi.dashboard(projectId),
        ]);
        setSelectedProject(detail);
        setDashboard(summary);
      } else {
        setSelectedProject(null);
        setDashboard(null);
      }
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to load projects");
    } finally {
      setIsLoading(false);
    }
  }, [projectId, statusFilter]);

  useEffect(() => {
    // This effect synchronizes the project workspace with route and filter changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, [refresh]);

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

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-iron-100 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-iron-950">Project Workspace</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
            Central hub for RFQs, suppliers, documents, drawings, bids, and project readiness.
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
      {isLoading ? <Notice tone="neutral" message="Loading projects..." /> : null}

      <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
        <div className="space-y-6">
          <ProjectFilters status={statusFilter} onStatusChange={setStatusFilter} />
          <CreateProjectForm onSubmit={(payload) => void createProject(payload)} />
          <ProjectList
            projects={projects}
            selectedId={projectId}
            dashboards={dashboardByProjectId}
          />
        </div>
        {selectedProject && dashboard ? (
          <ProjectDetail
            project={selectedProject}
            dashboard={dashboard}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            onStatusChange={(value) => void updateStatus(value)}
            onArchive={() => void archiveProject()}
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
  onStatusChange,
}: {
  status: string;
  onStatusChange: (value: string) => void;
}) {
  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <h2 className="text-base font-semibold text-iron-950">Project Filters</h2>
      <select
        value={status}
        onChange={(event) => onStatusChange(event.target.value)}
        className="mt-4 w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
      >
        <option value="">All statuses</option>
        {projectStatuses.map((item) => (
          <option key={item} value={item}>
            {label(item)}
          </option>
        ))}
      </select>
    </div>
  );
}

function CreateProjectForm({ onSubmit }: { onSubmit: (payload: ProjectCreatePayload) => void }) {
  const [name, setName] = useState("");
  const [municipality, setMunicipality] = useState("");
  const [bidDueDate, setBidDueDate] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) return;
    onSubmit({
      name: name.trim(),
      municipality: municipality.trim() || undefined,
      bid_due_date: bidDueDate || undefined,
      status: "opportunity",
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
      </div>
      <button
        type="submit"
        className="mt-5 inline-flex items-center gap-2 rounded-md bg-iron-950 px-3 py-2 text-sm font-semibold text-white"
      >
        <FolderKanban className="h-4 w-4" />
        Create
      </button>
    </form>
  );
}

function ProjectList({
  projects,
  selectedId,
  dashboards,
}: {
  projects: Project[];
  selectedId: string | undefined;
  dashboards: Record<string, ProjectDashboard>;
}) {
  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <h2 className="text-base font-semibold text-iron-950">Projects</h2>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-iron-100 text-xs uppercase tracking-wide text-iron-500">
              <th className="py-2 pr-4">Name</th>
              <th className="py-2 pr-4">Municipality</th>
              <th className="py-2 pr-4">Status</th>
              <th className="py-2 pr-4">Bid Due</th>
              <th className="py-2 pr-4">RFQ Progress</th>
              <th className="py-2 pr-4">Document Count</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((project) => {
              const summary = dashboards[project.id];
              return (
                <tr
                  key={project.id}
                  className={[
                    "border-b border-iron-100 last:border-b-0",
                    selectedId === project.id ? "bg-iron-50" : "",
                  ].join(" ")}
                >
                  <td className="py-3 pr-4 font-medium text-iron-950">
                    <Link to={`/projects/${project.id}`}>{project.name}</Link>
                  </td>
                  <td className="py-3 pr-4 text-iron-800">
                    {project.municipality ?? "Unassigned"}
                  </td>
                  <td className="py-3 pr-4 text-iron-800">{label(project.status)}</td>
                  <td className="py-3 pr-4 text-iron-800">{project.bid_due_date ?? "Not set"}</td>
                  <td className="py-3 pr-4 text-iron-800">
                    {summary ? `${summary.readiness_percentage}%` : "Loading"}
                  </td>
                  <td className="py-3 pr-4 text-iron-800">
                    {summary ? summary.document_count : "Loading"}
                  </td>
                </tr>
              );
            })}
            {projects.length === 0 ? (
              <tr>
                <td className="py-3 text-iron-500" colSpan={6}>
                  No projects found.
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
  activeTab,
  onTabChange,
  onStatusChange,
  onArchive,
}: {
  project: Project;
  dashboard: ProjectDashboard;
  activeTab: string;
  onTabChange: (tab: string) => void;
  onStatusChange: (status: ProjectStatus) => void;
  onArchive: () => void;
}) {
  return (
    <div className="space-y-6">
      <div className="rounded-md border border-iron-100 bg-white p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="text-xs uppercase tracking-wide text-iron-500">
              {project.project_number ?? "Project"}
            </div>
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
          </div>
        </div>
      </div>

      <DashboardWidgets dashboard={dashboard} project={project} />

      <div className="rounded-md border border-iron-100 bg-white">
        <div className="flex overflow-x-auto border-b border-iron-100">
          {tabs.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => onTabChange(tab)}
              className={[
                "px-4 py-3 text-sm font-medium",
                activeTab === tab ? "text-iron-950" : "text-iron-500",
              ].join(" ")}
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

function DashboardWidgets({ dashboard, project }: { dashboard: ProjectDashboard; project: Project }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <Widget icon={<Activity className="h-4 w-4" />} label="RFQ readiness" value={`${dashboard.readiness_percentage}%`} />
      <Widget icon={<FileStack className="h-4 w-4" />} label="Documents" value={String(dashboard.document_count)} />
      <Widget icon={<FolderKanban className="h-4 w-4" />} label="Supplier coverage" value={String(dashboard.supplier_count)} />
      <Widget icon={<CalendarDays className="h-4 w-4" />} label="Bid due" value={project.bid_due_date ?? "Not set"} />
      <Widget icon={<FileStack className="h-4 w-4" />} label="Drawings" value={String(dashboard.drawing_count)} />
      <Widget icon={<Activity className="h-4 w-4" />} label="RFQs" value={String(dashboard.rfq_count)} />
      <Widget icon={<Activity className="h-4 w-4" />} label="Bid status" value={label(dashboard.bid_status)} />
      <Widget icon={<CalendarDays className="h-4 w-4" />} label="Tender close" value={project.tender_closing_date ?? "Not set"} />
    </div>
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

function TabBody({
  tab,
  project,
  dashboard,
}: {
  tab: string;
  project: Project;
  dashboard: ProjectDashboard;
}) {
  const summaries: Record<string, string> = {
    Overview: project.notes ?? "Project overview notes will live here.",
    RFQs: `${dashboard.rfq_count} RFQ packages linked to this project.`,
    Documents: `${dashboard.document_count} documents linked to this project.`,
    Suppliers: `${dashboard.supplier_count} suppliers linked to this project.`,
    Drawings: `${dashboard.drawing_count} drawings linked to this project.`,
    Estimating: "Estimating workspace is reserved for future takeoff and costing.",
    Activity: "Activity stream is reserved for future audit events.",
  };
  return <p className="text-sm leading-6 text-iron-500">{summaries[tab]}</p>;
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
  const className =
    tone === "error"
      ? "border-signal-red bg-white text-signal-red"
      : "border-iron-100 bg-white text-iron-500";
  return <div className={`rounded-md border px-4 py-3 text-sm ${className}`}>{message}</div>;
}

function label(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
