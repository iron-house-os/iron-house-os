import { LibraryDocument } from "./documents";
import { Project } from "./projects";
import { RFQPackage } from "./rfqPackages";
import { apiFetch } from "./client";

export type TenderStatus =
  | "new"
  | "reviewing"
  | "bidding"
  | "submitted"
  | "awarded"
  | "lost"
  | "no_bid";

export type Tender = {
  id: string;
  title: string;
  tender_number: string | null;
  source: string | null;
  source_url: string | null;
  owner: string | null;
  municipality: string | null;
  closing_date: string | null;
  site_meeting_date: string | null;
  question_deadline: string | null;
  project_address: string | null;
  description: string | null;
  status: TenderStatus;
  estimated_value: number | null;
  metadata: Record<string, unknown>;
  project_id: string | null;
  rfq_package_id: string | null;
  document_ids: string[];
  suggested_supplier_categories: string[];
  created_at: string;
  updated_at: string;
};

export type TenderList = {
  items: Tender[];
  total: number;
};

export type TenderDocumentIntake = {
  title: string;
  category: string;
  storage_uri?: string;
  description?: string;
  metadata?: Record<string, unknown>;
};

export type TenderCreatePayload = {
  title: string;
  tender_number?: string;
  source?: string;
  source_url?: string;
  owner?: string;
  municipality?: string;
  closing_date?: string;
  site_meeting_date?: string;
  question_deadline?: string;
  project_address?: string;
  description?: string;
  status?: TenderStatus;
  estimated_value?: number;
  metadata?: Record<string, unknown>;
};

export type TenderIntakePayload = TenderCreatePayload & {
  documents?: TenderDocumentIntake[];
};

export type TenderIntakeResult = {
  tender: Tender;
  project: Project;
  rfq_package: RFQPackage;
  documents: LibraryDocument[];
  suggested_supplier_categories: string[];
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await apiFetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const tenderStatuses: TenderStatus[] = [
  "new",
  "reviewing",
  "bidding",
  "submitted",
  "awarded",
  "lost",
  "no_bid",
];

export const tendersApi = {
  list: (status?: string) => {
    const suffix = status ? `?status=${encodeURIComponent(status)}` : "";
    return request<TenderList>(`/tenders${suffix}`);
  },
  detail: (id: string) => request<Tender>(`/tenders/${id}`),
  create: (payload: TenderCreatePayload) =>
    request<Tender>("/tenders", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  update: (id: string, payload: Partial<TenderCreatePayload>) =>
    request<Tender>(`/tenders/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  intake: (payload: TenderIntakePayload) =>
    request<TenderIntakeResult>("/tenders/intake", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
