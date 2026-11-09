import { apiFetch } from "./client";

export type DrawingDiscipline = "civil" | "traffic" | "structural" | "electrical" | "landscape" | "environmental" | "unknown";

export type DrawingSheetType =
  | "cover"
  | "general_notes"
  | "civil_plan"
  | "profile"
  | "cross_section"
  | "traffic_control"
  | "esc"
  | "landscape"
  | "details"
  | "specification"
  | "addenda"
  | "unknown";

export type DrawingSheetInput = {
  sheet_number?: string | null;
  title: string;
  filename?: string | null;
  revision?: string | null;
  scale?: string | null;
  raw_text?: string | null;
};

export type DrawingSetAnalyzeRequest = {
  project_name?: string | null;
  municipality?: string | null;
  sheets: DrawingSheetInput[];
};

export type DrawingSheetAnalysis = {
  sheet_number?: string | null;
  title: string;
  filename?: string | null;
  discipline: DrawingDiscipline;
  sheet_type: DrawingSheetType;
  revision?: string | null;
  scale?: string | null;
  municipality_hints: string[];
  detected_keywords: string[];
  warnings: string[];
};

export type DrawingSetAnalysisResponse = {
  project_name?: string | null;
  municipality?: string | null;
  sheet_count: number;
  disciplines: Record<string, number>;
  sheet_types: Record<string, number>;
  revisions: Record<string, number>;
  municipality_hints: string[];
  warnings: string[];
  sheets: DrawingSheetAnalysis[];
};

export type DrawingExtractionStatus = "completed" | "partial" | "ocr_required" | "failed";
export type DrawingIssueSeverity = "info" | "warning" | "critical";

export type DrawingPageExtraction = {
  page_number: number;
  character_count: number;
  text_preview?: string | null;
  extraction_warning?: string | null;
};

export type DrawingQuantityCandidate = {
  description: string;
  quantity: number;
  unit: string;
  page_number: number;
  source_text: string;
  confidence: "low" | "medium" | "high";
  requires_verification: true;
};

export type DrawingIssue = {
  issue_type: "constructability" | "municipal_standard";
  severity: DrawingIssueSeverity;
  title: string;
  detail: string;
  page_number?: number | null;
  evidence?: string | null;
  requires_review: true;
};

export type CivilDrawingAnalysis = {
  analysis_version: "build-206-v1";
  source: {
    document_id: string;
    project_id: string;
    storage_uri: string;
    original_filename: string;
    sha256_hash: string;
    size_bytes: number;
    page_count: number;
  };
  title: string;
  municipality?: string | null;
  extraction_status: DrawingExtractionStatus;
  analyzed_at: string;
  text_character_count: number;
  pages: DrawingPageExtraction[];
  quantity_candidates: DrawingQuantityCandidate[];
  constructability_issues: DrawingIssue[];
  municipal_standard_issues: DrawingIssue[];
  warnings: string[];
};

export type CivilDrawingAnalysisList = {
  items: CivilDrawingAnalysis[];
  total: number;
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

async function uploadRequest<T>(path: string, formData: FormData): Promise<T> {
  const response = await apiFetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const drawingIntelligenceApi = {
  analyze: (payload: DrawingSetAnalyzeRequest) =>
    request<DrawingSetAnalysisResponse>("/drawing-intelligence/analyze", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  ingest: (payload: {
    file: File;
    project_id: string;
    title?: string;
    municipality?: string;
  }) => {
    const formData = new FormData();
    formData.append("file", payload.file);
    formData.append("project_id", payload.project_id);
    if (payload.title) formData.append("title", payload.title);
    if (payload.municipality) formData.append("municipality", payload.municipality);
    return uploadRequest<CivilDrawingAnalysis>("/drawing-intelligence/ingest", formData);
  },
  projectAnalyses: (projectId: string) =>
    request<CivilDrawingAnalysisList>(`/drawing-intelligence/projects/${projectId}`),
  detail: (documentId: string) =>
    request<CivilDrawingAnalysis>(`/drawing-intelligence/${documentId}`),
  reanalyze: (documentId: string, municipality?: string) =>
    request<CivilDrawingAnalysis>(`/drawing-intelligence/${documentId}/reanalyze`, {
      method: "POST",
      body: JSON.stringify({ municipality: municipality || null }),
    }),
};
