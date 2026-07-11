export type DocumentAuditEvent = {
  action: string;
  document_id?: string;
  project_id?: string;
  outcome: string;
  actor?: string;
  request_id?: string;
  metadata?: Record<string, unknown>;
  occurred_at: string;
};

export type DocumentAuditEventList = {
  items: DocumentAuditEvent[];
  total: number;
};

export type DocumentAuditFilters = {
  limit?: number;
  action?: string;
  outcome?: string;
  actor?: string;
  project_id?: string;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const documentAuditApi = {
  list: async (filters: DocumentAuditFilters = {}): Promise<DocumentAuditEventList> => {
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== "") query.set(key, String(value));
    });
    const response = await fetch(`${API_BASE_URL}/documents/audit-events?${query.toString()}`);
    if (!response.ok) throw new Error(`Request failed with ${response.status}`);
    return response.json() as Promise<DocumentAuditEventList>;
  },
};
