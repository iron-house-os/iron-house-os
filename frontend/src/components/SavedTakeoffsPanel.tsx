import { useState } from "react";

import { takeoffPersistenceApi, TakeoffList } from "../api/takeoffPersistence";

type Props = {
  projectId?: string | null;
};

export function SavedTakeoffsPanel({ projectId }: Props) {
  const [takeoffs, setTakeoffs] = useState<TakeoffList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function loadTakeoffs() {
    if (!projectId) {
      setError("Open a project before loading saved takeoffs.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      setTakeoffs(await takeoffPersistenceApi.listForProject(projectId));
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to load saved takeoffs");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-base font-semibold text-iron-950">Saved Takeoffs</h2>
          <p className="mt-1 text-sm text-iron-500">Review takeoff records attached to this project.</p>
        </div>
        <button type="button" onClick={loadTakeoffs} disabled={isLoading} className="rounded-md border border-iron-100 px-4 py-2 text-sm font-semibold text-iron-800">
          {isLoading ? "Loading..." : "Load takeoffs"}
        </button>
      </div>
      {error ? <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
      {takeoffs ? <div className="mt-4 space-y-2 text-sm text-iron-700">{takeoffs.items.map((item) => <div key={item.id} className="rounded-md border border-iron-100 p-3">{item.status} - {new Date(item.created_at).toLocaleString()} - {item.notes ?? item.id}</div>)}{takeoffs.total === 0 ? <div>No saved takeoffs yet.</div> : null}</div> : null}
    </div>
  );
}
