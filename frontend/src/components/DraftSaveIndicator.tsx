import { DraftSaveStatus } from "../hooks/useWorkflowDraft";

const labels: Record<DraftSaveStatus, string> = {
  idle: "Draft starts saving after you enter information",
  loading: "Loading saved draft…",
  saving: "Saving draft…",
  saved: "Draft saved",
  recovery: "Recovered unsaved work from this device",
  conflict: "Newer work exists. Reload before editing further.",
  offline: "Server unavailable. Recovery copy kept on this device.",
};

export function DraftSaveIndicator({ status, lastSavedAt }: { status: DraftSaveStatus; lastSavedAt: string | null }) {
  const danger = status === "conflict" || status === "offline";
  return (
    <div
      role="status"
      className={`rounded-md border px-3 py-2 text-sm ${danger ? "border-amber-200 bg-amber-50 text-amber-900" : "border-iron-100 bg-iron-50 text-iron-600"}`}
    >
      {labels[status]}
      {lastSavedAt && status === "saved" ? ` · ${new Date(lastSavedAt).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}` : ""}
    </div>
  );
}
