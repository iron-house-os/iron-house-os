import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { WorkflowDraft, workflowDraftsApi } from "../api/workflowDrafts";
import { modulePathWithProjectContext, readEffectiveProjectContext } from "../utils/projectContext";

const steps = [
  { label: "1. Capture customer quote", path: "/customer-quotes", detail: "Turn verbal customer information into a durable IHOS opportunity and quote." },
  { label: "2. Create or select project", path: "/projects", detail: "Open the project workspace for tender, estimate, or awarded-job work." },
  { label: "3. Register documents", path: "/documents", detail: "Add drawings, specs, addenda, and source documents." },
  { label: "4. Run takeoff", path: "/quantity-takeoff", detail: "Generate BOQ items, readiness checks, and estimating handoff items." },
  { label: "5. Build estimate", path: "/estimating", detail: "Convert scope into estimate lines, calculate pricing, and export workbooks." },
  { label: "6. Build RFQs", path: "/rfq-automation", detail: "Create supplier package drafts from takeoff and estimate categories." },
  { label: "7. Final bid package", path: "/bid-package", detail: "Review assumptions, exclusions, risks, and final bid readiness." },
];

export function MVPWorkflowPage() {
  const location = useLocation();
  const activeProject = readEffectiveProjectContext(location.search);
  const [drafts, setDrafts] = useState<WorkflowDraft[]>([]);
  const [draftError, setDraftError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void workflowDraftsApi.list()
      .then((result) => {
        if (active) setDrafts(result.items);
      })
      .catch((reason) => {
        if (active) setDraftError(reason instanceof Error ? reason.message : "Unable to load unfinished work.");
      });
    return () => { active = false; };
  }, []);

  async function discardDraft(draft: WorkflowDraft) {
    try {
      await workflowDraftsApi.cancel(draft.id, draft.revision);
      setDrafts((current) => current.filter((item) => item.id !== draft.id));
    } catch (reason) {
      setDraftError(reason instanceof Error ? reason.message : "Unable to discard the draft.");
    }
  }

  return (
    <section className="space-y-6">
      <div className="border-b border-iron-100 pb-6">
        <h1 className="text-3xl font-semibold text-iron-950">IHOS MVP Workflow</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
          Build 51 operating page for the first usable internal web app flow: project, documents, takeoff, estimate, RFQs, and bid package.
        </p>
      </div>
      <section className="rounded-xl border border-brand-gold/30 bg-white p-5 shadow-sm" aria-labelledby="resume-work-title">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 id="resume-work-title" className="text-xl font-semibold text-iron-950">Resume unfinished work</h2>
            <p className="mt-1 text-sm text-iron-500">IHOS keeps your in-progress forms here until you finish or discard them.</p>
          </div>
          <span className="rounded-full bg-iron-100 px-3 py-1 text-xs font-semibold text-iron-700">{drafts.length} open</span>
        </div>
        {draftError ? <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{draftError}</div> : null}
        {drafts.length ? (
          <div className="mt-4 divide-y divide-iron-100 rounded-md border border-iron-100">
            {drafts.map((draft) => (
              <div key={draft.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="font-semibold text-iron-950">{draft.title}</div>
                  <div className="mt-1 text-xs text-iron-500">Saved {new Date(draft.last_saved_at).toLocaleString()}</div>
                </div>
                <div className="flex gap-2">
                  <Link to={resumePath(draft)} className="rounded-md bg-iron-950 px-3 py-2 text-sm font-semibold text-white">Continue</Link>
                  <button type="button" onClick={() => void discardDraft(draft)} className="rounded-md border border-iron-200 px-3 py-2 text-sm font-semibold text-iron-700">Discard</button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-4 rounded-md bg-iron-50 p-4 text-sm text-iron-500">No unfinished forms. Start anywhere below; your entries will save automatically.</p>
        )}
      </section>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {steps.map((step) => (
          <Link key={step.label} to={modulePathWithProjectContext(step.path, activeProject)} className="rounded-md border border-iron-100 bg-white p-5 transition hover:border-iron-300">
            <div className="text-base font-semibold text-iron-950">{step.label}</div>
            <p className="mt-2 text-sm leading-6 text-iron-500">{step.detail}</p>
            <div className="mt-4 text-sm font-semibold text-iron-800">Open module</div>
          </Link>
        ))}
      </div>
    </section>
  );
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
