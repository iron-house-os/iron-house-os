import { apiFetch } from "./client";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type ChatStatus = { enabled: boolean; configured: boolean; model: string; mode: string; voice_supported: boolean };
export type ChatMessage = { id: string; role: "user" | "assistant"; content: string; status: string; created_at: string };
export type ChatConversation = { id: string; title: string; created_at: string; updated_at: string };
export type ChatReply = { conversation: ChatConversation; user_message: ChatMessage; assistant_message: ChatMessage };

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
  send: (message: string, conversationId?: string) => apiFetch(`${API_BASE_URL}/iron-house-chat/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id: conversationId ?? null }),
  }).then(read<ChatReply>),
};

