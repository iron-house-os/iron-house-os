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

export type DocumentAuditSummary = {
  total: number;
  by_action: Record<string, number>;
  by_outcome: Record<string, number>;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

function buildQuery(filters: DocumentAuditFilters = {}): string {
  const query = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  return query.toString();
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) throw new Error(`Request failed with ${response.status}`);
  return response.json() as Promise<T>;
}

export const documentAuditApi = {
  list: (filters: DocumentAuditFilters = {}) => {
    const query = buildQuery(filters);
    return getJson<DocumentAuditEventList>(`/documents/audit-events${query ? `?${query}` : ""}`);
  },
  summary: (filters: DocumentAuditFilters = {}) => {
    const query = buildQuery(filters);
    return getJson<DocumentAuditSummary>(`/documents/audit-events/summary${query ? `?${query}` : ""}`);
  },
  csvUrl: (filters: DocumentAuditFilters = {}) => {
    const query = buildQuery(filters);
    return `${API_BASE_URL}/documents/audit-events/export.csv${query ? `?${query}` : ""}`;
  },
};
