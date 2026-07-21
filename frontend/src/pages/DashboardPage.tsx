import { ClipboardList, Database, FileStack, FolderKanban, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Project, projectsApi } from "../api/projects";
import { RFQPackage, rfqPackagesApi } from "../api/rfqPackages";
import { Supplier, suppliersApi } from "../api/suppliers";

type DashboardState = {
  projects: Project[];
  suppliers: Supplier[];
  rfqs: RFQPackage[];
};

const emptyState: DashboardState = {
  projects: [],
  suppliers: [],
  rfqs: [],
};

export function DashboardPage() {
  const [state, setState] = useState<DashboardState>(emptyState);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setIsLoading(true);
    setError(null);
    try {
      const [projectList, supplierList, rfqList] = await Promise.all([
        projectsApi.list(),
        suppliersApi.list({}),
        rfqPackagesApi.list(),
      ]);
      setState({
        projects: projectList.items,
        suppliers: supplierList.items,
        rfqs: rfqList.items,
      });
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to load dashboard");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  const activeProjects = state.projects.filter(
    (project) => !["completed", "archived"].includes(project.status),
  );
  const tenderingProjects = state.projects.filter((project) => project.status === "tendering");
  const openRfqs = state.rfqs.filter((rfq) => !["issued", "closed"].includes(rfq.status));
  const supplierContacts = state.suppliers.reduce(
    (total, supplier) => total + supplier.contacts.length,
    0,
  );

  return (
    <section className="space-y-6">
      <div className="ihos-brand-surface relative overflow-hidden rounded-xl border border-brand-gold/30 px-6 py-6 text-white shadow-brand">
        <div className="relative z-10 flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-4">
            <img src="/os-logo-256.png" alt="" className="h-20 w-20 rounded-2xl border border-brand-gold/30 object-cover shadow-lg" />
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-gold">Iron House Contracting</div>
              <h1 className="mt-2 text-3xl font-semibold text-brand-silver">Iron House Dashboard</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-100">
                Operating snapshot for tenders, projects, RFQs, suppliers, and estimating.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => void refresh()}
            className="inline-flex items-center justify-center gap-2 rounded-md border border-brand-gold/40 bg-white/10 px-3 py-2 text-sm font-medium text-white transition hover:bg-brand-gold hover:text-brand-black"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {error ? (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <DashboardCard icon={FolderKanban} label="Active Projects" value={activeProjects.length} href="/projects" />
        <DashboardCard icon={ClipboardList} label="Tendering" value={tenderingProjects.length} href="/projects" />
        <DashboardCard icon={FileStack} label="Open RFQs" value={openRfqs.length} href="/rfq-builder" />
        <DashboardCard icon={Database} label="Suppliers" value={state.suppliers.length} href="/suppliers" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <div className="rounded-md border border-iron-100 bg-white p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-iron-950">Current Work</h2>
              <p className="mt-1 text-sm text-iron-500">Latest project records in the system.</p>
            </div>
            <Link to="/projects" className="text-sm font-semibold text-signal-blue">
              Open projects
            </Link>
          </div>

          <div className="mt-4 overflow-hidden rounded-md border border-iron-100">
            <table className="w-full text-left text-sm">
              <thead className="bg-iron-50 text-xs uppercase tracking-wide text-iron-500">
                <tr>
                  <th className="px-3 py-2">Project</th>
                  <th className="px-3 py-2">Municipality</th>
                  <th className="px-3 py-2">Bid Due</th>
                  <th className="px-3 py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {state.projects.slice(0, 8).map((project) => (
                  <tr key={project.id} className="border-t border-iron-100">
                    <td className="px-3 py-2 font-medium text-iron-950">
                      <Link to={`/projects/${project.id}`}>{project.name}</Link>
                    </td>
                    <td className="px-3 py-2 text-iron-600">{project.municipality ?? "—"}</td>
                    <td className="px-3 py-2 text-iron-600">{project.bid_due_date ?? "—"}</td>
                    <td className="px-3 py-2 text-iron-600">{project.status}</td>
                  </tr>
                ))}
                {!state.projects.length ? (
                  <tr>
                    <td className="px-3 py-4 text-iron-500" colSpan={4}>
                      No projects yet. Create the first one in Project Workspace.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>

        <aside className="space-y-6">
          <div className="rounded-md border border-iron-100 bg-white p-5">
            <h2 className="text-base font-semibold text-iron-950">MVP Health</h2>
            <dl className="mt-4 space-y-3 text-sm">
              <HealthRow label="Supplier contacts" value={supplierContacts} />
              <HealthRow label="RFQ packages" value={state.rfqs.length} />
              <HealthRow label="Project records" value={state.projects.length} />
            </dl>
          </div>

          <div className="rounded-md border border-iron-100 bg-white p-5">
            <h2 className="text-base font-semibold text-iron-950">Next Actions</h2>
            <div className="mt-4 grid gap-2 text-sm">
              <QuickLink href="/projects" label="Create or update project" />
              <QuickLink href="/suppliers" label="Add supplier contact" />
              <QuickLink href="/rfq-builder" label="Build RFQ package" />
              <QuickLink href="/estimating" label="Build estimate" />
            </div>
          </div>
        </aside>
      </div>
    </section>
  );
}

function DashboardCard({
  icon: Icon,
  label,
  value,
  href,
}: {
  icon: typeof FolderKanban;
  label: string;
  value: number;
  href: string;
}) {
  return (
    <Link to={href} className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium text-iron-500">{label}</div>
        <Icon className="h-5 w-5 text-brand-gold" />
      </div>
      <div className="mt-4 text-3xl font-semibold text-iron-950">{value}</div>
    </Link>
  );
}

function HealthRow({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-iron-500">{label}</dt>
      <dd className="font-semibold text-iron-950">{value}</dd>
    </div>
  );
}

function QuickLink({ href, label }: { href: string; label: string }) {
  return (
    <Link className="rounded-md border border-iron-100 px-3 py-2 font-medium text-iron-800 transition hover:border-brand-gold hover:bg-brand-gold/10" to={href}>
      {label}
    </Link>
  );
}

