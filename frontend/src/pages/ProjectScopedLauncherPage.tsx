import { BookOpen, Calculator, FileStack, Table2 } from "lucide-react";
import { Link, useParams } from "react-router-dom";

export function ProjectScopedLauncherPage() {
  const { projectId, tool } = useParams();
  const label = toolLabel(tool);
  const projectName = projectId ?? "selected project";
  const query = new URLSearchParams({ projectId: projectId ?? "", projectName }).toString();
  const target = toolTarget(tool, query);

  return (
    <section className="space-y-6">
      <div className="border-b border-iron-100 pb-6">
        <h1 className="text-3xl font-semibold text-iron-950">{label}</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
          Launching this tool with project context attached.
        </p>
      </div>

      <div className="rounded-md border border-iron-100 bg-white p-5">
        <div className="flex items-center gap-2 text-sm font-semibold text-iron-950">
          {toolIcon(tool)}
          Project context
        </div>
        <p className="mt-2 text-sm text-iron-500">Project ID: {projectId ?? "Not set"}</p>
        <Link className="mt-4 inline-flex rounded-md bg-iron-950 px-3 py-2 text-sm font-semibold text-white" to={target}>
          Open {label}
        </Link>
      </div>
    </section>
  );
}

function toolTarget(tool: string | undefined, query: string) {
  if (tool === "quotes") return `/quotes?${query}`;
  if (tool === "estimate") return `/estimating?${query}`;
  if (tool === "documents") return `/documents?${query}`;
  return `/rfq-builder?${query}`;
}

function toolLabel(tool: string | undefined) {
  if (tool === "quotes") return "Quote Comparison";
  if (tool === "estimate") return "Estimating";
  if (tool === "documents") return "Documents";
  return "RFQ Builder";
}

function toolIcon(tool: string | undefined) {
  if (tool === "quotes") return <Table2 className="h-4 w-4" />;
  if (tool === "estimate") return <Calculator className="h-4 w-4" />;
  if (tool === "documents") return <BookOpen className="h-4 w-4" />;
  return <FileStack className="h-4 w-4" />;
}
