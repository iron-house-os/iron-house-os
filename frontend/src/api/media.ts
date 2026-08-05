import { apiFetch } from "./client";

export type MediaCategory =
  | "job_photo"
  | "production_photo"
  | "inspection"
  | "equipment"
  | "flha"
  | "incident"
  | "deficiency"
  | "expense"
  | "receipt"
  | "backups";

export type MediaOperation = {
  type: "rotate" | "straighten" | "crop" | "brightness" | "contrast" | "clarity" | "draw" | "arrow" | "box" | "highlight" | "text";
  values: Record<string, unknown>;
};

export type MediaVersion = {
  id: string;
  asset_id: string;
  parent_version_id: string | null;
  document_id: string;
  version_number: number;
  action: "original" | "edit" | "replacement" | "restore";
  editor_id: string;
  editor_email: string;
  operations: MediaOperation[];
  change_summary: string | null;
  amendment_reason: string | null;
  created_at: string;
};

export type MediaAsset = {
  id: string;
  original_document_id: string;
  current_version_id: string;
  project_id: string | null;
  caption: string | null;
  captured_date: string | null;
  location: string | null;
  category: MediaCategory;
  controlled: boolean;
  created_by_email: string;
  versions: MediaVersion[];
  links: Array<{ record_type: string; record_id: string }>;
  created_at: string;
  updated_at: string;
};

export type UploadMediaPayload = {
  files: File[];
  projectId?: string;
  caption?: string;
  capturedDate?: string;
  location?: string;
  category: MediaCategory;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function jsonRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await apiFetch(API_BASE_URL + path, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? "Photo request failed with " + response.status);
  }
  return response.json() as Promise<T>;
}

function uploadForm<T>(path: string, form: FormData, onProgress?: (percent: number) => void): Promise<T> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", API_BASE_URL + path);
    request.withCredentials = true;
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100));
    };
    request.onerror = () => reject(new Error("Photo upload failed. Your local selection has been retained; retry when connected."));
    request.onload = () => {
      if (request.status >= 200 && request.status < 300) {
        resolve(JSON.parse(request.responseText) as T);
        return;
      }
      try {
        const payload = JSON.parse(request.responseText) as { detail?: string };
        reject(new Error(payload.detail ?? "Photo upload failed with " + request.status));
      } catch {
        reject(new Error("Photo upload failed with " + request.status));
      }
    };
    request.send(form);
  });
}

export const mediaApi = {
  upload: (payload: UploadMediaPayload, onProgress?: (percent: number) => void) => {
    const form = new FormData();
    payload.files.forEach((file) => form.append("files", file));
    if (payload.projectId) form.append("project_id", payload.projectId);
    if (payload.caption) form.append("caption", payload.caption);
    if (payload.capturedDate) form.append("captured_date", payload.capturedDate);
    if (payload.location) form.append("location", payload.location);
    form.append("category", payload.category);
    return uploadForm<MediaAsset[]>("/media", form, onProgress);
  },
  list: (params: { projectId?: string; recordType?: string; recordId?: string; documentIds?: string[] }) => {
    const query = new URLSearchParams();
    if (params.projectId) query.set("project_id", params.projectId);
    if (params.recordType) query.set("record_type", params.recordType);
    if (params.recordId) query.set("record_id", params.recordId);
    params.documentIds?.forEach((id) => query.append("document_ids", id));
    return jsonRequest<MediaAsset[]>("/media?" + query.toString());
  },
  contentUrl: (assetId: string, versionId?: string, download = false) => {
    const query = new URLSearchParams();
    if (versionId) query.set("version_id", versionId);
    if (download) query.set("download", "true");
    return API_BASE_URL + "/media/" + assetId + "/content" + (query.size ? "?" + query : "");
  },
  link: (assetId: string, recordType: string, recordId: string) =>
    jsonRequest<MediaAsset>("/media/" + assetId + "/links", {
      method: "POST",
      body: JSON.stringify({ record_type: recordType, record_id: recordId }),
    }),
  updateMetadata: (assetId: string, payload: Partial<Pick<MediaAsset, "caption" | "captured_date" | "project_id" | "location" | "category">>) =>
    jsonRequest<MediaAsset>("/media/" + assetId, { method: "PATCH", body: JSON.stringify(payload) }),
  addVersion: (assetId: string, file: Blob, payload: { action: "edit" | "replacement"; operations: MediaOperation[]; changeSummary?: string; amendmentReason?: string }) => {
    const form = new FormData();
    form.append("file", file, "photo-" + Date.now() + ".png");
    form.append("action", payload.action);
    form.append("operations", JSON.stringify(payload.operations));
    if (payload.changeSummary) form.append("change_summary", payload.changeSummary);
    if (payload.amendmentReason) form.append("amendment_reason", payload.amendmentReason);
    return uploadForm<MediaAsset>("/media/" + assetId + "/versions", form);
  },
  restore: (assetId: string, versionId: string, amendmentReason?: string) =>
    jsonRequest<MediaAsset>("/media/" + assetId + "/restore", {
      method: "POST",
      body: JSON.stringify({ version_id: versionId, amendment_reason: amendmentReason }),
    }),
};
