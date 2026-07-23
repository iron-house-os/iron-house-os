import { apiFetch } from "./client";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type ChatStatus = { enabled: boolean; configured: boolean; model: string; mode: string; voice_supported: boolean; memory_count: number };
export type ChatMessage = { id: string; role: "user" | "assistant"; content: string; status: string; created_at: string };
export type ChatConversation = { id: string; title: string; created_at: string; updated_at: string };
export type ChatReply = { conversation: ChatConversation; user_message: ChatMessage; assistant_message: ChatMessage };
export type MemoryImportResult = { imported: number; updated: number; skipped: number; total_project_memories: number };
export type ProjectMemory = {
  id: string;
  source_kind: string;
  source_id: string;
  title: string;
  content: string;
  authority: number;
  source_date: string | null;
  source_url: string | null;
  imported_by: string;
  created_at: string;
  updated_at: string;
};
export type BrainSearchOptions = { query?: string; sourceKind?: string; minAuthority?: number; limit?: number };

async function read<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Iron House Chat request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const ironHouseChatApi = {
  status: () => apiFetch(`${API_BASE_URL}/iron-house-chat/status`).then(read<ChatStatus>),
  conversations: () => apiFetch(`${API_BASE_URL}/iron-house-chat/conversations`).then(read<ChatConversation[]>),
  messages: (id: string) => apiFetch(`${API_BASE_URL}/iron-house-chat/conversations/${id}/messages`).then(read<ChatMessage[]>),
  searchBrain: ({ query = "", sourceKind = "", minAuthority = 0, limit = 25 }: BrainSearchOptions = {}) => {
    const params = new URLSearchParams({ q: query, min_authority: String(minAuthority), limit: String(limit) });
    if (sourceKind) params.set("source_kind", sourceKind);
    return apiFetch(`${API_BASE_URL}/iron-house-chat/brain/search?${params.toString()}`).then(read<ProjectMemory[]>);
  },
  importChatGpt: (file: File) => {
    const body = new FormData();
    body.append("export", file);
    return apiFetch(`${API_BASE_URL}/iron-house-chat/brain/import-chatgpt`, { method: "POST", body }).then(read<MemoryImportResult>);
  },
  send: (message: string, conversationId?: string) => apiFetch(`${API_BASE_URL}/iron-house-chat/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id: conversationId ?? null }),
  }).then(read<ChatReply>),
};
