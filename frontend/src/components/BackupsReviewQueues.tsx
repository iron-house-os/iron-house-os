import { useCallback, useEffect, useState } from "react";

import { BackupsIntake, BackupsReviewDestination } from "../api/backups";
import { financeApi } from "../api/finance";
import { mediaApi } from "../api/media";
import { BackupsDestinationSelect } from "./BackupsDestinationSelect";

const sections: Array<[BackupsReviewDestination, string, string]> = [
  ["finance_intake", "Finance intake", "Newly analyzed photos awaiting management routing."],
  ["finance_receipts", "Receipts", "Review-only receipt candidates; approval and export remain separate."],
  ["finance_invoices", "Invoices", "Review-only invoice candidates; nothing is posted or paid."],
  ["finance_packing_slips", "Packing Slips", "Review only; this does not confirm quantity, quality, acceptance, or project cost."],
];

export function BackupsReviewQueues() {
  const [items, setItems] = useState<BackupsIntake[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setItems((await financeApi.getBackupsReview()).items);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load Backups review queues.");
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  function routed(updated: BackupsIntake) {
    setItems((current) => updated.review_destination === "backups_needs_review"
      ? current.filter((item) => item.id !== updated.id)
      : current.map((item) => item.id === updated.id ? updated : item));
  }

  return <section className="rounded-md border border-iron-100 bg-white p-5">
    <h2 className="font-semibold text-iron-950">Backups review</h2>
    <p className="mt-1 text-sm text-iron-500">Management routing changes review location only. It never approves, posts, exports, reconciles, pays, or accepts a delivery.</p>
    {error ? <div role="alert" className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
    <div className="mt-4 grid gap-4 xl:grid-cols-2">
      {sections.map(([destination, title, description]) => {
        const queued = items.filter((item) => item.review_destination === destination);
        return <section key={destination} aria-labelledby={`backups-${destination}`} className="rounded-md border border-iron-100 p-4">
          <div className="flex items-baseline justify-between gap-3"><h3 id={`backups-${destination}`} className="font-semibold">{title}</h3><span className="text-xs text-iron-500">{queued.length}</span></div>
          <p className="mt-1 text-xs leading-5 text-iron-500">{description}</p>
          <div className="mt-3 grid gap-3">
            {queued.map((item) => <article key={item.id} className="grid gap-3 rounded-md bg-iron-50 p-3 sm:grid-cols-[72px_1fr]">
              <a href={mediaApi.contentUrl(item.media_id)} target="_blank" rel="noreferrer"><img src={mediaApi.contentUrl(item.media_id)} alt="Private Backups original" className="h-[72px] w-[72px] rounded-md object-cover" /></a>
              <div className="min-w-0"><div className="truncate text-sm font-semibold">{item.detected_type?.replaceAll("_", " ") ?? "Unknown item"}</div><div className="truncate text-xs text-iron-500">{item.uploader_email}</div><div className="mt-2"><BackupsDestinationSelect item={item} onRouted={routed} /></div></div>
            </article>)}
            {!queued.length ? <div className="rounded-md bg-iron-50 p-3 text-xs text-iron-500">No items in this queue.</div> : null}
          </div>
        </section>;
      })}
    </div>
  </section>;
}
