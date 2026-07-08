import {
  BarChart3,
  BookOpen,
  Building2,
  ClipboardList,
  Database,
  FileSearch,
  FileStack,
  FolderKanban,
  Gauge,
  Landmark,
  Ruler,
  Settings,
  Table2,
  Truck,
  type LucideIcon,
} from "lucide-react";

export type AppModule = {
  label: string;
  path: string;
  icon: LucideIcon;
  description: string;
  status: string;
};

export const modules: AppModule[] = [
  {
    label: "Dashboard",
    path: "/dashboard",
    icon: Gauge,
    description: "Operational snapshot for projects, bids, suppliers, and workload.",
    status: "MVP active",
  },
  {
    label: "MVP Workflow",
    path: "/mvp-workflow",
    icon: ClipboardList,
    description: "Step-by-step internal workflow from project setup to final bid package.",
    status: "Build 51 active",
  },
  {
    label: "Projects",
    path: "/projects",
    icon: FolderKanban,
    description: "Central workspace for RFQs, documents, suppliers, drawings, bids, and readiness.",
    status: "MVP active",
  },
  {
    label: "RFQ Builder",
    path: "/rfq-builder",
    icon: FileStack,
    description: "Create RFQ packages, select suppliers, register documents, and check readiness.",
    status: "MVP active",
  },
  {
    label: "Supplier Database",
    path: "/suppliers",
    icon: Database,
    description: "Supplier profiles, contacts, categories, and service area search.",
    status: "MVP active",
  },
  {
    label: "Estimating",
    path: "/estimating",
    icon: ClipboardList,
    description: "Production rate estimate builder with markups, risk, summary, and workbook export.",
    status: "MVP active",
  },
  {
    label: "Drawing Intelligence",
    path: "/drawing-intelligence",
    icon: FileSearch,
    description: "Classify drawing sheets, detect revisions, scales, disciplines, municipalities, and drawing-set warnings.",
    status: "Build 24 active",
  },
  {
    label: "Quantity Takeoff Engine",
    path: "/quantity-takeoff",
    icon: Ruler,
    description: "Manual register plus takeoff engine for BOQ rollups, readiness checks, conflicts, and estimating handoff.",
    status: "Build 29 active",
  },
  {
    label: "Municipality Intelligence",
    path: "/municipality-intelligence",
    icon: Landmark,
    description: "Municipal standards checklist with cost-impact flags, estimating notes, and RFQ notes.",
    status: "Build 26 active",
  },
  {
    label: "Quote Comparison",
    path: "/quotes",
    icon: Table2,
    description: "Manual supplier quote comparison with selected-vs-lowest pricing review.",
    status: "MVP active",
  },
  {
    label: "Tender Tracker",
    path: "/tenders",
    icon: Building2,
    description: "Manual tender intake and opportunity-to-project workspace flow.",
    status: "MVP active",
  },
  {
    label: "Document Library",
    path: "/documents",
    icon: BookOpen,
    description: "Metadata library for drawings, specs, addenda, RFQs, and future storage sync.",
    status: "MVP active",
  },
  {
    label: "Equipment",
    path: "/equipment",
    icon: Truck,
    description: "Fleet availability and cost placeholders.",
    status: "Model ready",
  },
  {
    label: "Reporting",
    path: "/reporting",
    icon: BarChart3,
    description: "KPI and performance reporting shell.",
    status: "Reserved",
  },
  {
    label: "Settings",
    path: "/settings",
    icon: Settings,
    description: "Environment, team, and integration settings shell.",
    status: "Reserved",
  },
];