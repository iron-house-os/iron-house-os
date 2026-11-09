import { apiFetch } from "./client";

export type CostCode = { code: string; name: string };

export const costCodesApi = {
  list: async (): Promise<{ items: CostCode[] }> => {
    const base = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
    const response = await apiFetch(`${base}/cost-codes`);
    if (!response.ok) throw new Error(`Request failed with ${response.status}`);
    return response.json() as Promise<{ items: CostCode[] }>;
  },
};
