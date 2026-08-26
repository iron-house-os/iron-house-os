import { apiFetch } from "./client";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type HelpCoachSource = {
  id: string;
  title: string;
  path: string;
};

export type HelpCoachReply = {
  answer: string;
  status: "completed" | "static_fallback" | "no_match" | "restricted";
  audience: "employee" | "foreman" | "management";
  mode: "read-only";
  sources: HelpCoachSource[];
};

async function read(response: Response): Promise<HelpCoachReply> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Help Coach request failed (${response.status})`);
  }
  return response.json() as Promise<HelpCoachReply>;
}

export const helpCoachApi = {
  send: (
    message: string,
    context: { route?: string; projectName?: string },
    signal?: AbortSignal,
  ) => apiFetch(`${API_BASE_URL}/help-coach/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      route: context.route ?? "",
      project_name: context.projectName ?? "",
    }),
    signal,
  }).then(read),
};
