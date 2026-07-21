import { Link } from "react-router-dom";
import { useLocation } from "react-router-dom";

import { modulePathWithProjectContext, readEffectiveProjectContext } from "../utils/projectContext";

const steps = [
  { label: "1. Create project", path: "/projects", detail: "Open the project workspace and create or select a bid project." },
  { label: "2. Register documents", path: "/documents", detail: "Add drawings, specs, addenda, and source documents." },
  { label: "3. Run takeoff", path: "/quantity-takeoff", detail: "Generate BOQ items, readiness checks, and estimating handoff items." },
  { label: "4. Build estimate", path: "/estimating", detail: "Convert scope into estimate lines, calculate pricing, and export workbooks." },
  { label: "5. Build RFQs", path: "/rfq-automation", detail: "Create supplier package drafts from takeoff and estimate categories." },
  { label: "6. Final bid package", path: "/bid-package", detail: "Review assumptions, exclusions, risks, and final bid readiness." },
];

export function MVPWorkflowPage() {
  const location = useLocation();
  const activeProject = readEffectiveProjectContext(location.search);
  return (
    <section className="space-y-6">
      <div className="border-b border-iron-100 pb-6">
        <h1 className="text-3xl font-semibold text-iron-950">IHOS MVP Workflow</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
          Build 51 operating page for the first usable internal web app flow: project, documents, takeoff, estimate, RFQs, and bid package.
        </p>
      </div>
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
