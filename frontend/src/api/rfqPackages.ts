export type RFQPackageStatus = "draft" | "assembling" | "ready" | "issued" | "closed";

export type SupplierRecipient = {
  id: string;
  supplier_id: string;
  supplier_name: string;
  category: string | null;
  status: string;
};

export type RFQPackageDocument = {
  id: string;
  document_type: string;
  title: string;
  required: boolean;
  storage_uri: string | null;
  metadata: Record<string, unknown>;
  status: string;
};

export type RFQPackage = {
  id: string;
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
  project_name?: string;
  scope_summary?: string;
  supplier_category_targets: string[];
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
  selectSuppliers: (id: string, payload: Omit<SupplierRecipient, "id" | "status">[]) =>
    request<RFQPackage>(`/rfqs/${id}/suppliers`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  registerDocuments: (id: string, payload: Omit<RFQPackageDocument, "id" | "status">[]) =>
    request<RFQPackage>(`/rfqs/${id}/documents`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  readiness: (id: string) => request<RFQReadiness>(`/rfqs/${id}/readiness`),
};
