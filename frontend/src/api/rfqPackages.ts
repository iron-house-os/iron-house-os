export type RFQPackageStatus = "draft" | "assembling" | "ready" | "issued" | "closed";
export type RFQRecipientStatus = "pending" | "sent" | "replied" | "bounced";
export type RFQPackageDocumentStatus = "pending" | "attached" | "not_applicable";

export type SupplierRecipientCreate = {
  supplier_id: string;
  supplier_name: string;
  category?: string | null;
  scope_items: string[];
};

export type SupplierRecipient = SupplierRecipientCreate & {
  id: string;
  status: RFQRecipientStatus;
  scope_summary?: string | null;
  status_note?: string | null;
};

export type RFQPackageDocumentCreate = {
  document_type: string;
  title: string;
  required: boolean;
  storage_uri?: string | null;
  status: RFQPackageDocumentStatus;
  metadata: Record<string, unknown>;
};

export type RFQPackageDocument = RFQPackageDocumentCreate & {
  id: string;
};

export type RFQPackage = {
  id: string;
  project_id?: string | null;
  title: string;
  project_name: string | null;
  scope_summary: string | null;
  due_at: string | null;
  status: RFQPackageStatus;
  supplier_category_targets: string[];
  metadata: Record<string, unknown>;
  recipients: SupplierRecipient[];
  documents: RFQPackageDocument[];
  created_at: string;
  updated_at: string;
};

export type RFQPackageList = {
  items: RFQPackage[];
  total: number;
};

export type RFQReadinessItem = {
  key: string;
  label: string;
  ready: boolean;
  detail: string;
};

export type RFQReadiness = {
  rfq_package_id: string;
  status: RFQPackageStatus;
  ready: boolean;
  score: number;
  items: RFQReadinessItem[];
};

export type RFQPackageCreatePayload = {
  title: string;
  project_id?: string;
  project_name?: string;
  scope_summary?: string;
  due_at?: string;
  supplier_category_targets: string[];
};

export type SupplierRFQPackageDraft = {
  recipient_id: string;
  supplier_id: string;
  supplier_name: string;
  category?: string | null;
  status: RFQRecipientStatus;
  subject: string;
  body: string;
  scope_items: string[];
  attachment_names: string[];
};

export type RFQPackageBuildResponse = {
  rfq_package_id: string;
  ready: boolean;
  blockers: string[];
  packages: SupplierRFQPackageDraft[];
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
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const rfqPackagesApi = {
  list: () => request<RFQPackageList>("/rfqs"),
  create: (payload: RFQPackageCreatePayload) =>
    request<RFQPackage>("/rfqs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  detail: (id: string) => request<RFQPackage>(`/rfqs/${id}`),
  updateStatus: (id: string, status: RFQPackageStatus) =>
    request<RFQPackage>(`/rfqs/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  selectSuppliers: (id: string, payload: SupplierRecipientCreate[]) =>
    request<RFQPackage>(`/rfqs/${id}/suppliers`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  generateScopes: (id: string, force = false) =>
    request<RFQPackage>(`/rfqs/${id}/supplier-scopes`, {
      method: "POST",
      body: JSON.stringify({ force }),
    }),
  updateRecipientStatus: (
    id: string,
    recipientId: string,
    status: RFQRecipientStatus,
    note?: string,
  ) =>
    request<RFQPackage>(`/rfqs/${id}/suppliers/${recipientId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status, note: note || null }),
    }),
  registerDocuments: (id: string, payload: RFQPackageDocumentCreate[]) =>
    request<RFQPackage>(`/rfqs/${id}/documents`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  updateDocumentStatus: (
    id: string,
    documentId: string,
    status: RFQPackageDocumentStatus,
    storageUri?: string,
  ) =>
    request<RFQPackage>(`/rfqs/${id}/documents/${documentId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status, storage_uri: storageUri || null }),
    }),
  readiness: (id: string) => request<RFQReadiness>(`/rfqs/${id}/readiness`),
  build: (id: string) =>
    request<RFQPackageBuildResponse>(`/rfqs/${id}/build`, {
      method: "POST",
    }),
};
