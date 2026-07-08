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

export const drawingIntelligenceApi = {
  analyze: (payload: DrawingSetAnalyzeRequest) =>
    request<DrawingSetAnalysisResponse>("/drawing-intelligence/analyze", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
