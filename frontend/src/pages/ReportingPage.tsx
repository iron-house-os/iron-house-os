import { BarChart3, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Project, projectsApi } from "../api/projects";
import { RFQPackage, rfqPackagesApi } from "../api/rfqPackages";
import { suppliersApi } from "../api/suppliers";
import { Tender, tendersApi } from "../api/tenders";

type ReportState = {
  projects: Project[];
  rfqs: RFQPackage[];
  tenders: Tender[];
  supplierCount: number;
};

const emptyState: ReportState = { projects: [], rfqs: [], tenders: [], supplierCount: 0 };
const money = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD", maximumFractionDigits: 0 });

export function ReportingPage() {
  const [state, setState] = useState<ReportState>(emptyState);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setIsLoading(true);
    setError(null);
    try {
      const [projects, rfqs, tenders, suppliers] = await Promise.all([
        projectsApi.list(), rfqPackagesApi.list(), tendersApi.list(), suppliersApi.list({}),
      ]);
      setState({ projects: projects.items, rfqs: rfqs.items, tenders: tenders.items, supplierCount: suppliers.total });
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to load reporting data");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, []);

  const activeProjects = state.projects.filter((project) => !["completed", "archived"].includes(project.status));
  const pipelineValue = activeProjects.reduce((total, project) => total + (project.contract_value ?? 0), 0);
  const openRfqs = state.rfqs.filter((rfq) => !["issued", "closed"].includes(rfq.status));
  const upcoming = useMemo(
    () => [...state.projects]
      .filter((project) => project.bid_due_date)
      .sort((left, right) => (left.bid_due_date ?? "").localeCompare(right.bid_due_date ?? ""))
      .slice(0, 8),
    [state.projects],
  );

  const statusCounts = state.projects.reduce<Record<string, number>>((counts, project) => {
    counts[project.status] = (counts[project.status] ?? 0) + 1;
    return counts;
  }, {});
  const maxStatusCount = Math.max(1, ...Object.values(statusCounts));

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-iron-100 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-iron-950">Reporting</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">Live bid-pipeline, project, RFQ, supplier, and deadline reporting from the OS records.</p>
        </div>
        <button type="button" onClick={() => void refresh()} className="inline-flex items-center gap-2 rounded-md border border-iron-100 bg-white px-3 py-2 text-sm font-semibold"><RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} /> Refresh</button>
      </div>

      {error ? <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <Metric label="Active projects" value={String(activeProjects.length)} />
        <Metric label="Tender records" value={String(state.tenders.length)} />
        <Metric label="Open RFQs" value={String(openRfqs.length)} />
        <Metric label="Suppliers" value={String(state.supplierCount)} />
        <Metric label="Pipeline value" value={money.format(pipelineValue)} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_1.4fr]">
        <div className="rounded-md border border-iron-100 bg-white p-5">
          <div className="flex items-center gap-2"><BarChart3 className="h-4 w-4" /><h2 className="font-semibold">Projects by status</h2></div>
          <div className="mt-5 space-y-4">
            {Object.entries(statusCounts).map(([status, count]) => (
              <div key={status}>
                <div className="flex justify-between text-sm"><span className="capitalize text-iron-700">{status}</span><span className="font-semibold">{count}</span></div>
                <div className="mt-2 h-2 rounded-full bg-iron-100"><div className="h-2 rounded-full bg-signal-blue" style={{ width: `${Math.max(8, count / maxStatusCount * 100)}%` }} /></div>
              </div>
            ))}
            {!Object.keys(statusCounts).length ? <p className="text-sm text-iron-500">No project data yet.</p> : null}
          </div>
        </div>

        <div className="overflow-hidden rounded-md border border-iron-100 bg-white">
          <div className="flex items-center justify-between p-5"><h2 className="font-semibold">Upcoming bid deadlines</h2><Link to="/projects" className="text-sm font-semibold text-signal-blue">Open projects</Link></div>
          <div aria-label="Upcoming bid deadlines" role="region" tabIndex={0} className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-left text-sm">
              <thead className="bg-iron-50 text-xs uppercase tracking-wide text-iron-500"><tr><th className="px-4 py-3">Project</th><th className="px-4 py-3">Due</th><th className="px-4 py-3">Municipality</th><th className="px-4 py-3">Status</th></tr></thead>
              <tbody>
                {upcoming.map((project) => <tr key={project.id} className="border-t border-iron-100"><td className="px-4 py-3 font-medium"><Link to={`/projects/${project.id}`}>{project.name}</Link></td><td className="px-4 py-3">{project.bid_due_date}</td><td className="px-4 py-3">{project.municipality ?? "—"}</td><td className="px-4 py-3 capitalize">{project.status}</td></tr>)}
                {!upcoming.length ? <tr><td colSpan={4} className="px-4 py-5 text-iron-500">No bid deadlines have been recorded.</td></tr> : null}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md border border-iron-100 bg-white p-5"><div className="text-sm text-iron-500">{label}</div><div className="mt-3 text-2xl font-semibold text-iron-950">{value}</div></div>;
}
