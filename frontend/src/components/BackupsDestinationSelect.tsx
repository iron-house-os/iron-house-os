import { useState } from "react";

import { BackupsIntake, BackupsReviewDestination, backupsApi } from "../api/backups";

const options: Array<[Exclude<BackupsReviewDestination, "finance_intake">, string]> = [
  ["finance_receipts", "Finance — Receipts"],
  ["finance_invoices", "Finance — Invoices"],
  ["finance_packing_slips", "Finance — Packing Slips"],
  ["backups_needs_review", "Backups — Needs Review"],
];

export function BackupsDestinationSelect({ item, disabled = false, onRouted }: {
  item: BackupsIntake;
  disabled?: boolean;
  onRouted: (item: BackupsIntake) => void;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function route(destination: Exclude<BackupsReviewDestination, "finance_intake">) {
    setSaving(true);
    setError(null);
    try {
      onRouted(await backupsApi.updateDestination(item.id, destination, item.routing_version));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to change the review destination.");
    } finally {
      setSaving(false);
    }
  }

  return <label className="grid gap-1 text-sm font-semibold text-iron-700">
    Review destination
    <select
      aria-label={`Review destination for ${item.id}`}
      value={item.review_destination ?? "finance_intake"}
      disabled={disabled || saving}
      onChange={(event) => void route(event.target.value as Exclude<BackupsReviewDestination, "finance_intake">)}
      className="rounded-md border border-iron-100 bg-white px-3 py-2 font-normal disabled:opacity-60"
    >
      <option value="finance_intake" disabled>Finance intake</option>
      {options.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
    </select>
    {error ? <span role="alert" className="text-xs font-normal text-red-700">{error}</span> : null}
  </label>;
}
