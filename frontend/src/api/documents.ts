export type DocumentCategory =
  | "drawing"
  | "specification"
  | "addendum"
  | "geotechnical"
  | "permit"
  | "traffic_control"
  | "environmental"
  | "quote_request"
  | "other";

export type DocumentStatus = "registered" | "active" | "superseded" | "archived";

export type DrawingMetadata = {
  sheet_number: string | null;
  title: string | null;
  discipline: string | null;
  revision: string | null;
  issue_date: string | null;
  storage_uri: string | null;
};

export type LibraryDocument = {
  id: string;
  title: string;
  category: DocumentCategory;
  status: DocumentStatus;
  project_id: string | null;
  rfq_package_id: string | null;
  tender_id: string | null;
  supplier_id: string | null;
  storage_uri: string | null;
  description: string | null;
  drawing: DrawingMetadata | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type DocumentList = {
  items: LibraryDocument[];
  total: number;
};

export type DocumentCreatePayload = {
  title: string;
  category: DocumentCategory;
  status?: DocumentStatus;
  project_id?: string;
  rfq_package_id?: string;
  tender_id?: string;
  supplier_id?: string;
  storage_uri?: string;
  description?: string;
  drawing?: Partial<DrawingMetadata>;
  metadata?: Record<string, unknown>;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
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

export const documentCategories: DocumentCategory[] = [
  "drawing",
  "specification",
  "addendum",
  "geotechnical",
  "permit",
  "traffic_control",
  "environmental",
  "quote_request",
  "other",
];

export const documentStatuses: DocumentStatus[] = [
  "registered",
  "active",
  "superseded",
  "archived",
];

export const documentsApi = {
  list: (params: {
    category?: string;
    status?: string;
    project_id?: string;
    rfq_package_id?: string;
    tender_id?: string;
  }) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value) query.set(key, value);
    });
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return request<DocumentList>(`/documents${suffix}`);
  },
  create: (payload: DocumentCreatePayload) =>
    request<LibraryDocument>("/documents", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  detail: (id: string) => request<LibraryDocument>(`/documents/${id}`),
  updateStatus: (id: string, status: DocumentStatus) =>
    request<LibraryDocument>(`/documents/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
};
