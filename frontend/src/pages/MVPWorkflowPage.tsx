import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { CustomerQuote, customerQuotesApi } from "../api/customerQuotes";
import { Project, ProjectLaunchDashboard, projectsApi } from "../api/projects";
import { WorkflowDraft, workflowDraftsApi } from "../api/workflowDrafts";
import { modulePathWithProjectContext, readEffectiveProjectContext, withProjectContext } from "../utils/projectContext";

const flowStages = ["Capture quote", "Record decision", "Award + job number", "Launch controls", "Deliver + closeout"];

const tenderTools = [
  { label: "Project workspace", path: "/projects", detail: "Open a formal tender or an existing project." },
  { label: "Documents", path: "/documents", detail: "Register drawings, specifications, addenda, and source files." },
  { label: "Quantity takeoff", path: "/quantity-takeoff", detail: "Prepare quantities and estimating handoff items." },
  { label: "Estimating", path: "/estimating", detail: "Build costs, pricing, risk, and the estimate workbook." },
  { label: "Supplier RFQs", path: "/rfq-automation", detail: "Prepare supplier package drafts and quote coverage." },
  { label: "Bid package", path: "/bid-package", detail: "Review scope, assumptions, exclusions, and bid readiness." },
];

type WorkQueueItem = {
  id: string;
  title: string;
  reference: string;
  stage: string;
  detail: string;
  nextLabel: string;
  nextPath: string;
  secondaryActions: { label: string; path: string }[];
};

export function MVPWorkflowPage() {
  const location = useLocation();
  const activeProject = readEffectiveProjectContext(location.search);
  const [drafts, setDrafts] = useState<WorkflowDraft[]>([]);
  const [quotes, setQuotes] = useState<CustomerQuote[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [launchByProjectId, setLaunchByProjectId] = useState<Record<string, ProjectLaunchDashboard>>({});
  const [loadErrors, setLoadErrors] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const launchControllers = new Set<AbortController>();
    void (async () => {
      const errors: string[] = [];
      const [draftResult, quoteResult, projectResult] = await Promise.allSettled([
        workflowDraftsApi.list(),
        customerQuotesApi.list(),
        projectsApi.list(),
      ]);
      if (!active) return;

      if (draftResult.status === "fulfilled") setDrafts(draftResult.value.items);
      else errors.push("Unfinished forms could not be loaded.");
      if (quoteResult.status === "fulfilled") setQuotes(quoteResult.value.items);
      else errors.push("Customer quotes could not be loaded.");

      if (projectResult.status === "fulfilled") {
        setProjects(projectResult.value.items);
        const awarded = projectResult.value.items.filter(
          (project) => project.status === "awarded" && project.project_number,
        );
        setLoadErrors(errors);
        setIsLoading(false);

        let nextIndex = 0;
        async function loadNextLaunch() {
          while (active && nextIndex < awarded.length) {
            const project = awarded[nextIndex];
            nextIndex += 1;
            const controller = new AbortController();
            launchControllers.add(controller);
            const timeout = window.setTimeout(() => controller.abort(), 8000);
            try {
              const launch = await projectsApi.launchDashboard(project.id, { signal: controller.signal });
              if (active) setLaunchByProjectId((current) => ({ ...current, [project.id]: launch }));
            } catch {
              if (active) {
                const message = `Launch status could not be loaded for ${project.name}.`;
                setLoadErrors((current) => current.includes(message) ? current : [...current, message]);
              }
            } finally {
              window.clearTimeout(timeout);
              launchControllers.delete(controller);
            }
          }
        }
        void Promise.all(Array.from({ length: Math.min(3, awarded.length) }, () => loadNextLaunch()));
        return;
      } else {
        errors.push("Projects could not be loaded.");
      }

      setLoadErrors(errors);
      setIsLoading(false);
    })();
    return () => {
      active = false;
      launchControllers.forEach((controller) => controller.abort());
      launchControllers.clear();
    };
  }, []);

  const workQueue = useMemo(
    () => buildMvpWorkQueue(quotes, projects, launchByProjectId),
    [launchByProjectId, projects, quotes],
  );

  async function discardDraft(draft: WorkflowDraft) {
    try {
      await workflowDraftsApi.cancel(draft.id, draft.revision);
      setDrafts((current) => current.filter((item) => item.id !== draft.id));
    } catch {
      setLoadErrors((current) => [...current, `Unable to discard ${draft.title}. Reload and try again.`]);
    }
  }

  return (
    <section className="space-y-6">
      <div className="rounded-xl border border-brand-gold/30 bg-iron-950 p-6 text-white shadow-brand">
        <div className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-gold">Quote to completed job</div>
        <h1 className="mt-2 text-3xl font-semibold">IHOS Guided Workflow</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-200">
          Start with what the customer told you, then follow one next action through quote, acceptance, job number, launch, and delivery.
        </p>
        <Link to="/customer-quotes" className="mt-5 inline-flex min-h-12 items-center rounded-md bg-brand-gold px-4 py-3 text-sm font-semibold text-brand-black">
          Start a verbal customer quote
        </Link>
      </div>

      <ol aria-label="Quote-to-job stages" className="grid gap-2 sm:grid-cols-5">
        {flowStages.map((stage, index) => (
          <li key={stage} className="rounded-md border border-iron-100 bg-white p-3 text-sm font-semibold text-iron-800">
            <span className="mr-2 text-brand-gold-dark">{index + 1}</span>{stage}
          </li>
        ))}
      </ol>

      {loadErrors.length ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900" role="status">
          <div className="font-semibold">Some live status is temporarily unavailable.</div>
          <ul className="mt-2 list-disc space-y-1 pl-5">{loadErrors.map((error) => <li key={error}>{error}</li>)}</ul>
          <p className="mt-2">Available work remains usable below.</p>
        </div>
      ) : null}

      <section className="rounded-xl border border-brand-gold/30 bg-white p-5 shadow-sm" aria-labelledby="active-work-title">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 id="active-work-title" className="text-xl font-semibold text-iron-950">What needs attention</h2>
            <p className="mt-1 text-sm text-iron-500">Each card gives the next safe action from IHOS records. Approval gates still apply.</p>
          </div>
          <span className="rounded-full bg-iron-100 px-3 py-1 text-xs font-semibold text-iron-700">
            {isLoading ? "Loading" : `${workQueue.length} active`}
          </span>
        </div>
        {workQueue.length ? (
          <div className="mt-4 grid gap-4 lg:grid-cols-2" aria-label="Active quote-to-job work queue">
            {workQueue.map((item) => (
              <article key={item.id} className="flex flex-col rounded-lg border border-iron-100 p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-wide text-brand-gold-dark">{item.stage}</div>
                    <h3 className="mt-1 text-lg font-semibold text-iron-950">{item.title}</h3>
                  </div>
                  <span className="rounded-md bg-iron-50 px-2 py-1 text-xs font-semibold text-iron-700">{item.reference}</span>
                </div>
                <p className="mt-3 flex-1 text-sm leading-6 text-iron-600">{item.detail}</p>
                <Link to={item.nextPath} className="mt-4 inline-flex min-h-12 items-center justify-center rounded-md bg-iron-950 px-4 py-3 text-sm font-semibold text-white">
                  {item.nextLabel}
                </Link>
                {item.secondaryActions.length ? (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {item.secondaryActions.map((action) => (
                      <Link key={action.label} to={action.path} className="inline-flex min-h-11 items-center rounded-md border border-iron-200 px-3 py-2 text-sm font-semibold text-iron-700">
                        {action.label}
                      </Link>
                    ))}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        ) : isLoading ? (
          <p className="mt-4 rounded-md bg-iron-50 p-4 text-sm text-iron-500">Loading active quotes and jobs…</p>
        ) : (
          <div className="mt-4 rounded-md bg-iron-50 p-4 text-sm text-iron-600">
            No active quotes or jobs need attention. Start a verbal quote or open the tender tools below.
          </div>
        )}
      </section>

      <section className="rounded-xl border border-brand-gold/30 bg-white p-5 shadow-sm" aria-labelledby="resume-work-title">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 id="resume-work-title" className="text-xl font-semibold text-iron-950">Resume unfinished forms</h2>
            <p className="mt-1 text-sm text-iron-500">Your in-progress forms remain here until you finish or discard them.</p>
          </div>
          <span className="rounded-full bg-iron-100 px-3 py-1 text-xs font-semibold text-iron-700">{drafts.length} open</span>
        </div>
        {drafts.length ? (
          <div className="mt-4 divide-y divide-iron-100 rounded-md border border-iron-100">
            {drafts.map((draft) => (
              <div key={draft.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="font-semibold text-iron-950">{draft.title}</div>
                  <div className="mt-1 text-xs text-iron-500">Saved {new Date(draft.last_saved_at).toLocaleString()}</div>
                </div>
                <div className="flex gap-2">
                  <Link to={resumePath(draft)} className="inline-flex min-h-11 items-center rounded-md bg-iron-950 px-3 py-2 text-sm font-semibold text-white">Continue</Link>
                  <button type="button" onClick={() => void discardDraft(draft)} className="min-h-11 rounded-md border border-iron-200 px-3 py-2 text-sm font-semibold text-iron-700">Discard</button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-4 rounded-md bg-iron-50 p-4 text-sm text-iron-500">No unfinished forms. Entries save automatically after you start.</p>
        )}
      </section>

      <section aria-labelledby="tender-tools-title">
        <h2 id="tender-tools-title" className="text-xl font-semibold text-iron-950">Formal tender and bid tools</h2>
        <p className="mt-1 text-sm text-iron-500">Use these modules for tender work that needs drawings, takeoff, RFQs, and a formal bid package.</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {tenderTools.map((tool) => (
            <Link key={tool.label} to={modulePathWithProjectContext(tool.path, activeProject)} className="rounded-md border border-iron-100 bg-white p-5 transition hover:border-iron-300">
              <div className="text-base font-semibold text-iron-950">{tool.label}</div>
              <p className="mt-2 text-sm leading-6 text-iron-500">{tool.detail}</p>
              <div className="mt-4 text-sm font-semibold text-iron-800">Open module</div>
            </Link>
          ))}
        </div>
      </section>
    </section>
  );
}

export function buildMvpWorkQueue(
  quotes: CustomerQuote[],
  projects: Project[],
  launchByProjectId: Record<string, ProjectLaunchDashboard>,
): WorkQueueItem[] {
  const items: WorkQueueItem[] = [];
  const activeQuoteProjectIds = new Set(
    quotes.filter((quote) => quote.status === "draft" || quote.status === "sent").map((quote) => quote.project_id),
  );
  const projectIds = new Set(projects.map((project) => project.id));

  for (const quote of quotes) {
    if (quote.status === "draft" || quote.status === "sent") {
      const issueStep = quote.status === "sent"
        ? {
            stage: "Customer decision",
            detail: `${formatMoney(quote.total)} approved revision is recorded as issued. Record acceptance, decline, or a revised scope when the customer responds.`,
            label: "Record customer decision",
            action: "decision",
          }
        : quote.issue_status === "ready_for_review"
          ? {
              stage: "Quote review",
              detail: `${formatMoney(quote.total)} revision is ready for management review. Approve the exact PDF revision before issuance.`,
              label: "Review quote",
              action: "review",
            }
          : quote.issue_status === "approved_for_issue"
            ? {
                stage: "Approved for issue",
                detail: `${formatMoney(quote.total)} revision is approved and immutable. Record how it was issued to the customer.`,
                label: "Record quote issuance",
                action: "issue",
              }
            : {
                stage: "Quote draft",
                detail: `${formatMoney(quote.total)} quote is saved but not approved. Finish it and submit the revision for review.`,
                label: "Finish quote",
                action: "edit",
              };
      items.push({
        id: `quote-${quote.id}`,
        title: `${quote.customer_name} — ${quote.project_name}`,
        reference: quote.quote_number,
        stage: issueStep.stage,
        detail: issueStep.detail,
        nextLabel: issueStep.label,
        nextPath: `/customer-quotes?quoteId=${encodeURIComponent(quote.id)}&action=${issueStep.action}`,
        secondaryActions: [{ label: "Open project", path: `/projects/${quote.project_id}` }],
      });
    } else if (quote.status === "accepted" && !projectIds.has(quote.project_id)) {
      items.push({
        id: `accepted-quote-${quote.id}`,
        title: `${quote.customer_name} — ${quote.project_name}`,
        reference: quote.job_number ?? quote.quote_number,
        stage: "Awarded job",
        detail: "The quote is accepted and its permanent job number is recorded. Open the awarded project to continue launch controls.",
        nextLabel: "Open awarded project",
        nextPath: `/projects/${quote.project_id}`,
        secondaryActions: [],
      });
    }
  }

  for (const project of projects) {
    if (
      project.status === "archived" ||
      project.status === "completed" ||
      (project.status === "opportunity" && activeQuoteProjectIds.has(project.id))
    ) continue;
    const projectContext = { id: project.id, name: project.name };
    if (project.status === "awarded") {
      const launch = launchByProjectId[project.id];
      const ready = launch?.mobilization_status === "ready";
      items.push({
        id: `project-${project.id}`,
        title: project.name,
        reference: project.project_number ?? "Awarded",
        stage: ready ? "Launch controls ready" : "Awarded job launch",
        detail: launch
          ? ready
            ? `All ${launch.checklist_total_count} start controls are confirmed. Continue into delivery while keeping budget, PO, safety, and documents current.`
            : `${launch.checklist_completed_count} of ${launch.checklist_total_count} start controls are confirmed. Next: ${launch.next_incomplete_control?.label ?? "review the launch dashboard"}`
          : "The job is awarded, but its launch summary is temporarily unavailable. Open the project workspace to continue safely.",
        nextLabel: ready ? "Begin project operations" : "Complete launch controls",
        nextPath: ready ? withProjectContext("/project-operations", projectContext) : `/projects/${project.id}`,
        secondaryActions: [
          { label: "Budget", path: withProjectContext("/finance", projectContext) },
          { label: "PO requests", path: withProjectContext("/request-po", projectContext) },
          { label: "Safety", path: withProjectContext("/safety-operations", projectContext) },
          { label: "Documents", path: withProjectContext("/documents", projectContext) },
        ],
      });
    } else if (project.status === "construction") {
      items.push({
        id: `project-${project.id}`,
        title: project.name,
        reference: project.project_number ?? "Active job",
        stage: "Active delivery",
        detail: "Continue field delivery, cost control, safety, documents, and daily records. When physical work is ending, complete the evidence-backed closeout controls before management marks the project complete.",
        nextLabel: "Continue project operations",
        nextPath: withProjectContext("/project-operations", projectContext),
        secondaryActions: [
          { label: "Finance", path: withProjectContext("/finance", projectContext) },
          { label: "PO requests", path: withProjectContext("/request-po", projectContext) },
          { label: "Safety", path: withProjectContext("/safety-operations", projectContext) },
          { label: "Documents", path: withProjectContext("/documents", projectContext) },
          { label: "Closeout controls", path: `/projects/${project.id}` },
        ],
      });
    } else {
      items.push({
        id: `project-${project.id}`,
        title: project.name,
        reference: project.project_number ?? (project.status === "tendering" ? "Tender" : "Opportunity"),
        stage: project.status === "tendering" ? "Tender in progress" : "Opportunity",
        detail: project.status === "tendering"
          ? "Continue documents, takeoff, estimating, supplier RFQs, and bid-package readiness."
          : "Review the opportunity and decide whether it belongs in Customer Quotes or the formal tender workflow.",
        nextLabel: "Open project workspace",
        nextPath: `/projects/${project.id}`,
        secondaryActions: [],
      });
    }
  }
  return items;
}

function resumePath(draft: WorkflowDraft) {
  const paths: Record<WorkflowDraft["workflow_type"], string> = {
    customer_quote: "/customer-quotes",
    estimate: "/estimating",
    purchase_order_request: "/request-po",
    supplier_quote_comparison: "/quotes",
  };
  const params = new URLSearchParams({ draftId: draft.id });
  if (draft.project_id) params.set("projectId", draft.project_id);
  return `${paths[draft.workflow_type]}?${params.toString()}`;
}

function formatMoney(value: string) {
  return new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD", maximumFractionDigits: 0 }).format(Number(value));
}
