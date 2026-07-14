import { apiFetch } from "./client";

export type Contact = {
  id: string;
  first_name: string;
  last_name: string | null;
  email: string | null;
  phone: string | null;
  role: string | null;
};

export type ContactCreatePayload = Omit<Contact, "id">;

export type Supplier = {
  id: string;
  name: string;
  category: string | null;
  service_area: string | null;
  website: string | null;
  notes: string | null;
  metadata: Record<string, unknown>;
  contacts: Contact[];
  created_at: string;
  updated_at: string;
};

export type SupplierList = {
  items: Supplier[];
  total: number;
};

export type SupplierCreatePayload = {
  name: string;
  category?: string;
  service_area?: string;
  website?: string;
  notes?: string;
  contacts?: ContactCreatePayload[];
  metadata?: Record<string, unknown>;
};

export type SupplierUpdatePayload = Partial<
  Pick<SupplierCreatePayload, "name" | "category" | "service_area" | "website" | "notes" | "metadata">
>;

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

export const suppliersApi = {
  list: (params: { search?: string; category?: string; service_area?: string }) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value) query.set(key, value);
    });
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return request<SupplierList>(`/suppliers${suffix}`);
  },
  create: (payload: SupplierCreatePayload) =>
    request<Supplier>("/suppliers", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  detail: (id: string) => request<Supplier>(`/suppliers/${id}`),
  update: (id: string, payload: SupplierUpdatePayload) =>
    request<Supplier>(`/suppliers/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  replaceContacts: (id: string, payload: ContactCreatePayload[]) =>
    request<Supplier>(`/suppliers/${id}/contacts`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
};
