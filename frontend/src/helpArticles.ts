import type { AuthUser } from "./api/auth";
import type { PortalRole } from "./contexts/AuthContext";
import { modules } from "./modules";

export type HelpAudience = AuthUser["role"];

export type HelpArticle = {
  id: string;
  title: string;
  task: string;
  summary: string;
  path: string;
  contextPaths: string[];
  roles: HelpAudience[];
  portalRoles?: Array<"employee" | "foreman">;
  keywords: string[];
  steps: string[];
  expectedResult: string;
  approvalNote?: string;
  featured?: boolean;
  kind: "task" | "module";
};

const managementRoles: HelpAudience[] = ["admin", "operations_manager", "estimator"];
const operationsRoles: HelpAudience[] = ["admin", "operations_manager"];

const taskArticles: HelpArticle[] = [
  {
    id: "employee-enter-time",
    title: "Enter my time",
    task: "Record the hours I worked",
    summary: "Add your hours to the correct day and job, then review them before saving.",
    path: "/employee-portal/time",
    contextPaths: ["/employee-portal/time"],
    roles: ["viewer", ...managementRoles],
    portalRoles: ["employee"],
    keywords: ["time", "hours", "timesheet", "shift", "job"],
    steps: [
      "Open Time in the Employee Portal.",
      "Choose the work date and the correct project.",
      "Enter your hours and the work details requested on the page.",
      "Review the date, project and total hours.",
      "Save or submit the entry.",
    ],
    expectedResult: "Your time entry is saved for supervisor or management review.",
    approvalNote: "A saved entry is not the same as payroll approval.",
    featured: true,
    kind: "task",
  },
  {
    id: "employee-submit-receipt",
    title: "Submit a receipt",
    task: "Send a purchase receipt to Financial Control",
    summary: "Upload a clear photo, check the extracted details and submit it for review.",
    path: "/employee-portal/receipts",
    contextPaths: ["/employee-portal/receipts", "/foreman-portal/receipts"],
    roles: ["viewer", ...managementRoles],
    portalRoles: ["employee", "foreman"],
    keywords: ["receipt", "expense", "reimbursement", "company card", "photo"],
    steps: [
      "Open Receipts in your portal.",
      "Take or select a clear photo of every receipt page.",
      "Check the vendor, date, payment method, taxes and total.",
      "Add the project or coding details you know.",
      "Submit the receipt for review.",
    ],
    expectedResult: "The receipt is queued for Financial Control review; it is not posted automatically.",
    approvalNote: "Financial Control reviews coding, totals and duplicates before approval or export.",
    featured: true,
    kind: "task",
  },
  {
    id: "employee-check-schedule",
    title: "Check my schedule",
    task: "See where and when I am scheduled",
    summary: "Open the schedule assigned to your portal and review the job details.",
    path: "/employee-portal/schedule",
    contextPaths: ["/employee-portal/schedule", "/foreman-portal/schedule"],
    roles: ["viewer", ...managementRoles],
    portalRoles: ["employee", "foreman"],
    keywords: ["schedule", "shift", "crew", "tomorrow", "where", "when"],
    steps: [
      "Open Schedule in your portal.",
      "Find the correct date.",
      "Review the project, start information and notes.",
      "Contact your supervisor if anything is missing or incorrect.",
    ],
    expectedResult: "You know the current assignment shown in Iron House OS.",
    approvalNote: "If field instructions conflict with the schedule, confirm with your supervisor.",
    featured: true,
    kind: "task",
  },
  {
    id: "field-complete-flha",
    title: "Complete the daily FLHA",
    task: "Record today’s tasks, hazards and controls",
    summary: "Verify actual site conditions, review every control and post the FLHA to the job folder.",
    path: "/employee-portal/safety",
    contextPaths: ["/employee-portal/safety", "/foreman-portal/safety"],
    roles: ["viewer", ...managementRoles],
    portalRoles: ["employee", "foreman"],
    keywords: ["flha", "safety", "hazard", "control", "assessment", "field level"],
    steps: [
      "Open Safety and select the correct project or job.",
      "Complete the rapid hazard screening for actual site conditions.",
      "Add each task, hazard, control and responsible person.",
      "Resolve every critical-hazard blocker and review the emergency details.",
      "Review the FLHA, then post it for crew acknowledgement and supervisor release.",
    ],
    expectedResult: "A versioned FLHA is saved in the job folder for acknowledgement and release.",
    approvalNote: "Help or AI suggestions never declare work safe. Stop work and contact the supervisor whenever conditions are unsafe or unclear.",
    featured: true,
    kind: "task",
  },
  {
    id: "field-request-po",
    title: "Request a purchase order",
    task: "Ask for approval before a purchase",
    summary: "Send the purchase details to the designated approver and wait for the approved PO number.",
    path: "/request-po",
    contextPaths: ["/request-po", "/employee-portal/request-po", "/foreman-portal/request-po"],
    roles: ["viewer", ...managementRoles],
    portalRoles: ["employee", "foreman"],
    keywords: ["po", "purchase order", "buy", "supplier", "approval", "material"],
    steps: [
      "Open Request PO.",
      "Select the correct project and supplier when known.",
      "Describe what is needed, the reason and the expected amount.",
      "Review the request and submit it.",
      "Wait for the approver’s decision and PO number before purchasing.",
    ],
    expectedResult: "A traceable PO request is sent for approval.",
    approvalNote: "Submitting a request does not authorize a purchase.",
    featured: true,
    kind: "task",
  },
  {
    id: "field-inspect-equipment",
    title: "Inspect small equipment",
    task: "Record an equipment condition before use",
    summary: "Check the item, record its condition and flag anything unsafe or needing repair.",
    path: "/employee-portal/small-equipment",
    contextPaths: ["/employee-portal/small-equipment", "/foreman-portal/small-equipment", "/equipment/field"],
    roles: ["viewer", ...managementRoles],
    portalRoles: ["employee", "foreman"],
    keywords: ["equipment", "inspection", "tool", "repair", "damage", "unsafe"],
    steps: [
      "Open Small Equipment and choose the employee and project.",
      "Identify the equipment type and asset.",
      "Check guards, controls, cords or hoses, leaks and damage.",
      "Choose the condition and add clear comments or photos.",
      "Review and submit the inspection.",
    ],
    expectedResult: "The condition is recorded and flagged items are visible to management.",
    approvalNote: "Remove unsafe equipment from service and notify the supervisor immediately.",
    featured: true,
    kind: "task",
  },
  {
    id: "foreman-crew-time",
    title: "Enter crew time",
    task: "Prepare the foreman daily timesheet",
    summary: "Record crew hours against the correct project and review the daily sheet.",
    path: "/foreman-portal/time",
    contextPaths: ["/foreman-portal/time"],
    roles: ["viewer", ...managementRoles],
    portalRoles: ["foreman"],
    keywords: ["crew time", "foreman", "daily timesheet", "hours", "labour"],
    steps: [
      "Open Time in the Foreman Portal.",
      "Choose the work date and project.",
      "Add each crew member and their hours.",
      "Check the crew total and work details.",
      "Save or submit the daily sheet for review.",
    ],
    expectedResult: "The daily crew timesheet is saved for management review.",
    approvalNote: "Review does not replace payroll approval.",
    featured: true,
    kind: "task",
  },
  {
    id: "foreman-record-production",
    title: "Record daily production",
    task: "Capture completed quantities and field progress",
    summary: "Save the day’s production against the correct job with supporting notes or photos.",
    path: "/foreman-portal/production",
    contextPaths: ["/foreman-portal/production", "/foreman-portal/loads"],
    roles: ["viewer", ...managementRoles],
    portalRoles: ["foreman"],
    keywords: ["production", "quantity", "loads", "progress", "foreman", "daily"],
    steps: [
      "Open Production or Loads in the Foreman Portal.",
      "Select the correct date and project.",
      "Enter the activity, quantity, unit and supporting details.",
      "Attach clear evidence when it is available.",
      "Review and save the record.",
    ],
    expectedResult: "A traceable daily production record is attached to the job.",
    featured: true,
    kind: "task",
  },
  {
    id: "management-verbal-quote",
    title: "Start a verbal quote",
    task: "Turn a customer request into a controlled quote record",
    summary: "Capture the customer, scope and assumptions before preparing or issuing a quote.",
    path: "/customer-quotes",
    contextPaths: ["/customer-quotes"],
    roles: managementRoles,
    keywords: ["verbal quote", "customer", "scope", "price", "acceptance", "award"],
    steps: [
      "Open Customer Quotes and start a new verbal quote.",
      "Record the customer, contact, site and scope requested.",
      "Add pricing, assumptions, exclusions and validity details.",
      "Review the draft before it is issued.",
      "Record customer acceptance only when evidence is available.",
    ],
    expectedResult: "A controlled quote record is ready for review, issue and eventual award handoff.",
    approvalNote: "Quote acceptance and project award remain explicit management actions.",
    featured: true,
    kind: "task",
  },
  {
    id: "management-create-project",
    title: "Create or open a project",
    task: "Set up the central project workspace",
    summary: "Create the project once, then use its workspace to reach documents, RFQs, estimating and readiness.",
    path: "/projects",
    contextPaths: ["/projects", "/p"],
    roles: managementRoles,
    keywords: ["project", "job", "workspace", "awarded", "setup", "job number"],
    steps: [
      "Open Projects and search before creating a new record.",
      "Open the existing project, or choose the correct stage for a new one.",
      "Enter the required customer, name and project details.",
      "Save the project and keep it selected as the active project.",
      "Use the project workspace for the next task.",
    ],
    expectedResult: "One central project record is available to the connected OS functions.",
    approvalNote: "Do not create a duplicate project when a matching job already exists.",
    featured: true,
    kind: "task",
  },
  {
    id: "management-build-estimate",
    title: "Build an estimate",
    task: "Prepare production costs, markups and risk",
    summary: "Build the estimate within the active project and review its assumptions before export.",
    path: "/estimating",
    contextPaths: ["/estimating"],
    roles: managementRoles,
    keywords: ["estimate", "cost", "markup", "production rate", "risk", "workbook"],
    steps: [
      "Open Estimating with the correct active project.",
      "Add the work items, quantities, production rates and costs.",
      "Add markups, risk and estimate notes.",
      "Review the summary and unresolved assumptions.",
      "Save the workspace or export the workbook for review.",
    ],
    expectedResult: "A saved, project-linked estimate is ready for internal review.",
    approvalNote: "Exporting an estimate does not approve a bid or customer price.",
    featured: true,
    kind: "task",
  },
  {
    id: "management-upload-document",
    title: "Add a project document",
    task: "Store a drawing, specification, addendum or other file",
    summary: "Upload the source file once, label it clearly and keep its revision traceable.",
    path: "/document-operations",
    contextPaths: ["/document-operations", "/documents"],
    roles: managementRoles,
    keywords: ["document", "upload", "drawing", "specification", "addendum", "revision", "file"],
    steps: [
      "Open Document Operations with the correct active project.",
      "Choose the file and the correct document type.",
      "Enter a clear title, date and revision information.",
      "Review the project and metadata.",
      "Upload the document and confirm it appears in the project record.",
    ],
    expectedResult: "A traceable project document is available to connected workflows.",
    approvalNote: "Preserve source documents; do not replace an old revision without recording the new one.",
    featured: true,
    kind: "task",
  },
  {
    id: "management-build-rfq",
    title: "Build an RFQ package",
    task: "Prepare supplier pricing requests",
    summary: "Select suppliers and controlled project documents, then review package readiness.",
    path: "/rfq-builder",
    contextPaths: ["/rfq-builder", "/rfq-automation", "/bid-package"],
    roles: managementRoles,
    keywords: ["rfq", "supplier", "quote", "package", "attachments", "bid"],
    steps: [
      "Open RFQ Builder with the correct active project.",
      "Define the requested scope and response date.",
      "Select the intended suppliers.",
      "Add only the correct controlled documents and revisions.",
      "Resolve readiness warnings before issuing anything.",
    ],
    expectedResult: "A project-linked RFQ package is ready for controlled review or issue.",
    approvalNote: "Readiness does not authorize sending or committing the company.",
    kind: "task",
  },
  {
    id: "operations-onboard-employee",
    title: "Onboard a new employee",
    task: "Create, review and activate a new-hire record",
    summary: "Use the controlled invitation and review process; restricted information stays restricted.",
    path: "/employee-onboarding",
    contextPaths: ["/employee-onboarding", "/worker-orientations"],
    roles: operationsRoles,
    keywords: ["employee", "onboarding", "new hire", "invitation", "orientation", "activate"],
    steps: [
      "Open Employee Onboarding and create the new-hire record.",
      "Generate and deliver the secure invitation.",
      "Review the returned package and request corrections if needed.",
      "Approve the package and complete required orientation evidence.",
      "Activate access only after deployment readiness passes.",
    ],
    expectedResult: "The employee has a reviewed onboarding record and appropriately controlled OS access.",
    approvalNote: "Activation is a management-controlled action; invitation completion alone is not approval.",
    kind: "task",
  },
];

const moduleArticles: HelpArticle[] = modules.map((module) => ({
  id: `module-${module.path.slice(1).replaceAll("/", "-") || "home"}`,
  title: module.label,
  task: `Learn what ${module.label} is for`,
  summary: module.description,
  path: module.path,
  contextPaths: [module.path],
  roles: managementRoles,
  keywords: [module.label, module.description, "module", "page"],
  steps: [
    `Open ${module.label} from the main menu.`,
    "Confirm you are working in the correct project when a project is shown.",
    "Read the page heading and any status or readiness message.",
    "Use the task controls available for your role.",
    "Return to Help before continuing if the result or approval is unclear.",
  ],
  expectedResult: `You can identify the purpose and current status of ${module.label}.`,
  kind: "module" as const,
}));

const workforceModuleArticles: HelpArticle[] = [
  {
    id: "module-employee-portal-workforce",
    title: "Employee Portal",
    task: "Find employee field tasks",
    summary: "Time, receipts, schedule, safety, equipment, records and personal details in one place.",
    path: "/employee-portal",
    contextPaths: ["/employee-portal"],
    roles: ["viewer"],
    portalRoles: ["employee"],
    keywords: ["employee", "portal", "field", "home"],
    steps: [
      "Open Employee Portal from the menu.",
      "Choose the task card that matches what you need to do.",
      "Complete one workspace at a time.",
      "Review the result message before leaving the page.",
    ],
    expectedResult: "You are in the correct employee workspace for the task.",
    kind: "module",
  },
  {
    id: "module-foreman-portal-workforce",
    title: "Foreman Portal",
    task: "Find crew and field-record tasks",
    summary: "Crew time, production, loads, forms, safety, photos and records in one place.",
    path: "/foreman-portal",
    contextPaths: ["/foreman-portal"],
    roles: ["viewer"],
    portalRoles: ["foreman"],
    keywords: ["foreman", "crew", "portal", "field", "home"],
    steps: [
      "Open Foreman Portal from the menu.",
      "Choose the crew or field-record task you need.",
      "Confirm the date and project before entering information.",
      "Review the result message before leaving the page.",
    ],
    expectedResult: "You are in the correct foreman workspace for the task.",
    kind: "module",
  },
];

export const helpArticles: HelpArticle[] = [...taskArticles, ...moduleArticles, ...workforceModuleArticles];

function normalizedPortalRole(portalRole: PortalRole): "employee" | "foreman" {
  return portalRole === "foreman" ? "foreman" : "employee";
}

export function helpArticlesForUser(role: HelpAudience, portalRole: PortalRole): HelpArticle[] {
  return helpArticles.filter((article) => {
    if (!article.roles.includes(role)) return false;
    if (role !== "viewer" || !article.portalRoles) return true;
    return article.portalRoles.includes(normalizedPortalRole(portalRole));
  });
}

function pathMatchLength(pathname: string, contextPath: string): number {
  if (pathname === contextPath || pathname.startsWith(`${contextPath}/`)) return contextPath.length;
  return -1;
}

export function contextualHelpArticle(pathname: string, articles: HelpArticle[]): HelpArticle | null {
  if (!pathname) return null;
  let best: { article: HelpArticle; length: number } | null = null;
  for (const article of articles) {
    for (const contextPath of article.contextPaths) {
      const length = pathMatchLength(pathname, contextPath);
      if (length > (best?.length ?? -1)) best = { article, length };
    }
  }
  return best?.article ?? null;
}

function searchableText(article: HelpArticle): string {
  return [article.title, article.task, article.summary, article.expectedResult, ...article.keywords, ...article.steps]
    .join(" ")
    .toLowerCase();
}

export function searchHelpArticles(articles: HelpArticle[], query: string): HelpArticle[] {
  const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (!terms.length) return articles;
  return articles.filter((article) => {
    const text = searchableText(article);
    return terms.every((term) => text.includes(term));
  });
}
