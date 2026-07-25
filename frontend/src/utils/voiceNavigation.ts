export type VoiceNavigationTarget = {
  label: string;
  path: string;
};

const TARGETS: Array<VoiceNavigationTarget & { aliases: string[] }> = [
  { label: "Iron House Chat", path: "/iron-house-chat", aliases: ["iron house chat", "chat"] },
  { label: "Safety Operations", path: "/safety-operations", aliases: ["safety operations", "safety controls"] },
  { label: "Safety Program", path: "/safety-program", aliases: ["safety program", "safety page", "safety"] },
  { label: "Project Operations", path: "/project-operations", aliases: ["project operations"] },
  { label: "Projects", path: "/projects", aliases: ["project workspace", "projects"] },
  { label: "Document Operations", path: "/document-operations", aliases: ["document operations"] },
  { label: "Document Library", path: "/documents", aliases: ["document library", "documents"] },
  { label: "RFQ Automation", path: "/rfq-automation", aliases: ["rfq automation"] },
  { label: "RFQ Builder", path: "/rfq-builder", aliases: ["rfq builder", "rfqs", "rfq"] },
  { label: "Bid Package", path: "/bid-package", aliases: ["bid package generator", "bid package"] },
  { label: "Supplier Database", path: "/suppliers", aliases: ["supplier database", "suppliers"] },
  { label: "Drawing Intelligence", path: "/drawing-intelligence", aliases: ["drawing intelligence", "drawings"] },
  { label: "Quantity Takeoff", path: "/quantity-takeoff", aliases: ["quantity takeoff engine", "quantity takeoff", "takeoff"] },
  {
    label: "Municipality Intelligence",
    path: "/municipality-intelligence",
    aliases: ["municipality intelligence", "municipal standards"],
  },
  { label: "Quote Comparison", path: "/quotes", aliases: ["quote comparison", "quotes"] },
  { label: "Tender Tracker", path: "/tenders", aliases: ["tender tracker", "tenders"] },
  { label: "Financial Control", path: "/finance", aliases: ["financial control", "finances", "finance"] },
  { label: "Vehicle Tracking", path: "/vehicle-tracking", aliases: ["vehicle tracking", "vehicles"] },
  { label: "Employee Portal", path: "/employee-portal", aliases: ["employee portal"] },
  { label: "Foreman Portal", path: "/foreman-portal", aliases: ["foreman portal"] },
  { label: "Operator Portal", path: "/operator-portal", aliases: ["operator portal"] },
  { label: "MVP Workflow", path: "/mvp-workflow", aliases: ["mvp workflow", "bid workflow", "workflow"] },
  { label: "Estimating", path: "/estimating", aliases: ["estimating", "estimate builder", "estimates"] },
  { label: "Equipment", path: "/equipment", aliases: ["equipment"] },
  { label: "Reporting", path: "/reporting", aliases: ["reporting", "reports"] },
  { label: "Settings", path: "/settings", aliases: ["settings"] },
  { label: "Dashboard", path: "/dashboard", aliases: ["dashboard", "home"] },
];

const NAVIGATION_PREFIX =
  /^(?:please\s+)?(?:open|show(?:\s+me)?|go\s+to|take\s+me\s+to|navigate\s+to|bring\s+me\s+to)\s+(?:the\s+)?/;

function normalize(command: string): string {
  return command
    .trim()
    .toLocaleLowerCase("en-CA")
    .replace(/[.,!?;:]+$/g, "")
    .replace(/\s+/g, " ");
}

export function resolveVoiceNavigation(command: string): VoiceNavigationTarget | null {
  const normalized = normalize(command);
  if (!NAVIGATION_PREFIX.test(normalized)) return null;

  const destination = normalized.replace(NAVIGATION_PREFIX, "").replace(/\s+page$/, "").trim();
  for (const target of TARGETS) {
    if (target.aliases.includes(destination)) return { label: target.label, path: target.path };
  }
  return null;
}
