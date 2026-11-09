import { useState } from "react";

import { takeoffPersistenceApi, TakeoffRead } from "../api/takeoffPersistence";
import { QuantityItem, QuantityRegisterResponse } from "../api/takeoff";

type Props = {
  projectId?: string | null;
  items: QuantityItem[];
  quantityRegister?: QuantityRegisterResponse | null;
};

export function TakeoffSavePanel({ projectId, items, quantityRegister }: Props) {
  const [saved, setSaved] = useState<TakeoffRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  async function saveTakeoff() {
    if (!projectId) {
      setError("Open a project before saving a takeoff.");
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      setSaved(
        await takeoffPersistenceApi.save({
          project_id: projectId,
          status: "draft",
          notes: "Saved from Quantity Takeoff page.",
          items,
          quantity_register: quantityRegister,
        }),
      );
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to save takeoff");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-base font-semibold text-iron-950">Save Takeoff</h2>
          <p className="mt-1 text-sm text-iron-500">Attach the current quantity register to the active project so readiness can see it.</p>
        </div>
        <button type="button" onClick={saveTakeoff} disabled={isSaving || !items.length} className="rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white">
          {isSaving ? "Saving..." : "Save takeoff"}
        </button>
      </div>
      {error ? <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
      {saved ? <div className="mt-4 rounded-md border border-iron-100 p-3 text-sm text-iron-700">Saved takeoff: {saved.id}</div> : null}
    </div>
  );
}
