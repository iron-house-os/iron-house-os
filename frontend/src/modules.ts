import {
  BarChart3,
  BookOpen,
  Building2,
  ClipboardList,
  Database,
  FileStack,
  FolderKanban,
  Gauge,
  Settings,
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
    status: "Phase 1 shell",
  },
  {
    label: "Projects",
    path: "/projects",
    icon: FolderKanban,
    description: "Project records, scopes, milestones, and linked bid activity.",
    status: "Model ready",
  },
  {
    label: "RFQ Builder",
    path: "/rfq-builder",
    icon: FileStack,
    description: "Create RFQ packages, select suppliers, register documents, and check readiness.",
    status: "Phase 2 foundation",
  },
  {
    label: "Supplier Database",
    path: "/suppliers",
    icon: Database,
    description: "Supplier profiles, contacts, categories, and coverage areas.",
    status: "Model ready",
  },
  {
    label: "Estimating",
    path: "/estimating",
    icon: ClipboardList,
    description: "Future takeoff, production, and cost database workspace.",
    status: "Reserved",
  },
  {
    label: "Tender Tracker",
    path: "/tenders",
    icon: Building2,
    description: "Tender watchlist and municipality opportunity intake.",
    status: "Model ready",
  },
  {
    label: "Document Library",
    path: "/documents",
    icon: BookOpen,
    description: "Drawings, specifications, addenda, and bid files.",
    status: "Model ready",
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
