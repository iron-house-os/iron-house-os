export type DocumentCategory =
  | "drawing"
  | "specification"
  | "addendum"
  | "geotechnical"
  | "permit"
  | "traffic_control"
  | "environmental"
  | "quote_request"
  | "quote"
  | "photo"
  | "testing"
  | "other";

export type DocumentStatus = "registered" | "active" | "current" | "superseded" | "archived";

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

export type DocumentUploadResponse = {
  document: LibraryDocument;
  original_filename: string;
  safe_filename: string;
  extension: string;
  content_type: string | null;
  size_bytes: number;
  sha256_hash: string;
  duplicate_document_ids: string[];
};

export type DocumentIntegrity = {
  document_id: string;
  storage_uri: string | null;
  file_exists: boolean;
  sha256_hash: string | null;
  size_bytes: number | null;
  duplicate_document_ids: string[];
};

export type RFQAttachmentManifestItem = {
  document_id: string;
  title: string;
  category: DocumentCategory;
  status: DocumentStatus;
  storage_uri: string | null;
  filename: string | null;
  size_bytes: number | null;
  sha256_hash: string | null;
};

export type RFQAttachmentManifest = {
  item_count: number;
  total_size_bytes: number;
  items: RFQAttachmentManifestItem[];
  warnings: string[];
};

export type SignedDownloadTokenResponse = {
  token: string;
  expires_in: number;
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

async function uploadRequest<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) throw new Error(`Request failed with ${response.status}`);
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
  "quote",
  "photo",
  "testing",
  "other",
];

export const documentStatuses: DocumentStatus[] = [
  "registered",
  "active",
  "current",
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
  upload: (payload: { file: File; title?: string; category: DocumentCategory; project_id?: string; description?: string; revision?: string }) => {
    const formData = new FormData();
    formData.append("file", payload.file);
    if (payload.title) formData.append("title", payload.title);
    formData.append("category", payload.category);
    if (payload.project_id) formData.append("project_id", payload.project_id);
    if (payload.description) formData.append("description", payload.description);
    if (payload.revision) formData.append("revision", payload.revision);
    return uploadRequest<DocumentUploadResponse>("/documents/upload", formData);
  },
  detail: (id: string) => request<LibraryDocument>(`/documents/${id}`),
  downloadUrl: (id: string) => `${API_BASE_URL}/documents/${id}/download`,
  requestDownloadToken: (id: string) =>
    request<SignedDownloadTokenResponse>(`/documents/${id}/download-token`),
  signedDownloadUrl: (token: string) =>
    `${API_BASE_URL}/documents/signed-download?token=${encodeURIComponent(token)}`,
  integrity: (id: string) => request<DocumentIntegrity>(`/documents/${id}/integrity`),
  attachmentManifest: (documentIds: string[]) =>
    request<RFQAttachmentManifest>("/documents/attachment-manifest", {
      method: "POST",
      body: JSON.stringify({ document_ids: documentIds }),
    }),
  updateStatus: (id: string, status: DocumentStatus) =>
    request<LibraryDocument>(`/documents/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
};
