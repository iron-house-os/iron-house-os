import { Camera, RefreshCw, ShieldCheck } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { BackupsIntake, BackupsRoutableDestination, backupsApi } from "../api/backups";
import { mediaApi } from "../api/media";
import { UniversalPhotoField } from "../components/UniversalPhotoField";
import { useAuth } from "../contexts/AuthContext";

export function BackupsPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<BackupsIntake[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [uploadedMediaIds, setUploadedMediaIds] = useState<string[]>([]);
  const [note, setNote] = useState("");
  const [projectHint, setProjectHint] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isManagement = ["admin", "operations_manager"].includes(user?.role ?? "");

  const refresh = useCallback(async () => {
    try {
      setItems((await backupsApi.list()).items);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load Backups.");
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!files.length && !uploadedMediaIds.length) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    let remaining = [...uploadedMediaIds];
    try {
      if (!remaining.length) {
        const uploaded = await mediaApi.upload({
          files,
          caption: note.trim() || "Backups intake",
          category: "backup",
        });
        remaining = uploaded.map((item) => item.id);
        setUploadedMediaIds(remaining);
        setFiles([]);
      }
      const count = remaining.length;
      while (remaining.length) {
        await backupsApi.create({
          media_id: remaining[0],
          note: note.trim() || null,
          project_hint: projectHint.trim() || null,
        });
        remaining = remaining.slice(1);
        setUploadedMediaIds(remaining);
      }
      setNote("");
      setProjectHint("");
      setMessage(`${count} photo${count === 1 ? "" : "s"} stored. The daily controller will route each one for review.`);
      await refresh();
    } catch (reason) {
      setUploadedMediaIds(remaining);
      setError(reason instanceof Error ? reason.message : "Unable to submit these photos. Unfinished items were retained for retry.");
    } finally {
      setBusy(false);
    }
  }

  async function runController() {
    setBusy(true);
    setError(null);
    try {
      const result = await backupsApi.runDaily();
      setMessage(`Controller complete: ${result.routed} routed, ${result.needs_review} in triage, ${result.failed} failed.`);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to run the controller.");
    } finally {
      setBusy(false);
    }
  }

  async function route(item: BackupsIntake, destination: BackupsRoutableDestination) {
    if (!item.review_destination) return;
    setBusy(true);
    setError(null);
    try {
      await backupsApi.route(item.id, item.review_destination, destination);
      setMessage("Review destination updated. No financial action was taken.");
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to route this intake.");
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function retry(id: string) {
    setBusy(true);
    setError(null);
    try {
      await backupsApi.retry(id);
      setMessage("Intake queued for one clean retry.");
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to retry this intake.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-6">
      <header className="ihos-brand-surface rounded-xl border border-brand-gold/30 px-6 py-6 text-white shadow-brand">
        <div className="flex items-start gap-4">
          <div className="grid h-12 w-12 place-items-center rounded-xl border border-brand-gold/40 bg-white/10 text-brand-gold"><Camera /></div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-gold">Document intake</div>
            <h1 className="mt-2 text-3xl font-semibold text-brand-silver">Backups</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-100">
              Save multiple original photos now. Daily routing creates review-only records and never approves, posts, pays, or accepts documents.
            </p>
          </div>
        </div>
      </header>

      <form onSubmit={submit} className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
        <h2 className="font-semibold text-iron-950">Add photos</h2>
        <p className="mt-1 text-sm text-iron-500">Take several photos or choose multiple images. Every immutable original stays in private media storage.</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <UniversalPhotoField files={files} onFilesChange={(next) => { setFiles(next); setUploadedMediaIds([]); setMessage(null); setError(null); }} category="backup" label="Backup photos" />
          <label className="grid gap-1 text-sm font-medium text-iron-700">Optional note<textarea value={note} onChange={(event) => setNote(event.target.value)} maxLength={2000} className="min-h-24 rounded-md border border-iron-100 px-3 py-2" /></label>
          <label className="grid gap-1 text-sm font-medium text-iron-700">Optional project hint<input value={projectHint} onChange={(event) => setProjectHint(event.target.value)} maxLength={255} className="rounded-md border border-iron-100 px-3 py-2" /></label>
        </div>
        <button disabled={busy || (!files.length && !uploadedMediaIds.length)} className="mt-4 rounded-md bg-brand-gold px-4 py-2 text-sm font-semibold text-brand-black disabled:opacity-50">
          {busy ? "Saving…" : uploadedMediaIds.length ? `Retry ${uploadedMediaIds.length} intake${uploadedMediaIds.length === 1 ? "" : "s"}` : `Store ${files.length} photo${files.length === 1 ? "" : "s"} in Backups`}
        </button>
      </form>

      {message ? <div role="status" className="rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">{message}</div> : null}
      {error ? <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}

      <section className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><h2 className="font-semibold text-iron-950">{isManagement ? "Company queue" : "My submissions"}</h2><p className="mt-1 text-sm text-iron-500">Originals remain private; routed records always require review.</p></div>
          {isManagement ? <button type="button" disabled={busy} onClick={() => void runController()} className="inline-flex items-center gap-2 rounded-md border border-brand-gold px-3 py-2 text-sm font-semibold"><RefreshCw className="h-4 w-4" />Run daily controller</button> : null}
        </div>
        <div className="mt-4 grid gap-3">
          {items.map((item) => (
            <article key={item.id} className="grid gap-4 rounded-md border border-iron-100 p-4 sm:grid-cols-[96px_1fr]">
              <a href={mediaApi.contentUrl(item.media_id)} target="_blank" rel="noreferrer" className="block">
                <img src={mediaApi.contentUrl(item.media_id)} alt="Private Backups original" className="h-24 w-24 rounded-md object-cover" />
              </a>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <StatusPill status={item.status} />
                  <span className="text-xs font-medium text-iron-500">{new Date(item.upload_timestamp).toLocaleString("en-CA")}</span>
                  {isManagement ? <span className="text-xs text-iron-500">{item.uploader_email} · {item.uploader_role.replaceAll("_", " ")}</span> : null}
                </div>
                <div className="mt-2 text-sm text-iron-700">{item.detected_type ? item.detected_type.replaceAll("_", " ") : "Awaiting classification"}{item.confidence !== null ? ` · ${Math.round(item.confidence * 100)}% confidence` : ""}</div>
                {item.classification_source ? <div className="mt-1 text-xs text-iron-500">Classification source: {classificationSourceLabel(item.classification_source)}</div> : null}
                {item.project_hint ? <div className="mt-1 text-sm text-iron-500">Project hint: {item.project_hint}</div> : null}
                {item.note ? <div className="mt-1 text-sm text-iron-500">{item.note}</div> : null}
                {item.sensitive_quarantine ? <div className="mt-2 inline-flex items-center gap-2 text-sm font-semibold text-amber-800"><ShieldCheck className="h-4 w-4" />Sensitive-content quarantine; external AI was skipped.</div> : null}
                {item.error ? <div className="mt-2 text-sm text-red-700">{item.error}</div> : null}
                {isManagement && item.processed_at && item.review_destination ? <label className="mt-3 grid max-w-sm gap-1 text-sm font-semibold text-iron-700">Review destination<select aria-label={`Destination for ${item.id}`} disabled={busy} value={item.review_destination} onChange={(event) => void route(item, event.target.value as BackupsRoutableDestination)} className="rounded-md border border-iron-100 bg-white px-3 py-2 font-normal"><option value="finance_intake" disabled>Finance — Intake</option><option value="finance_receipts">Finance — Receipts</option><option value="finance_invoices">Finance — Invoices</option><option value="finance_packing_slips">Finance — Packing Slips</option><option value="backups_needs_review">Backups — Needs Review</option></select></label> : null}
                {!isManagement && item.review_destination ? <div className="mt-2 text-xs text-iron-500">Submitted for management review.</div> : null}
                {item.destination_record_id ? <div className="mt-2 text-xs text-iron-500">Legacy review record: {item.destination_type} · {item.destination_record_id}</div> : null}
                <div className="mt-2 text-xs text-iron-500">{item.audit_history.length} audit event(s) · {item.attempt_count} controller attempt(s)</div>
                {isManagement && !item.destination_record_id && (item.review_destination === null || item.review_destination === "finance_intake") && ["failed", "needs_review"].includes(item.status) ? <button type="button" disabled={busy} onClick={() => void retry(item.id)} className="mt-3 text-sm font-semibold text-brand-gold-dark underline">Queue one retry</button> : null}
              </div>
            </article>
          ))}
          {!items.length ? <div className="rounded-md bg-iron-50 p-4 text-sm text-iron-500">No Backups submissions yet.</div> : null}
        </div>
      </section>
    </section>
  );
}

function classificationSourceLabel(source: string) {
  if (source === "openai_api") return "AI-assisted classification";
  if (source === "local_ocr") return "Local OCR";
  if (source === "local_sensitive_screen") return "Local sensitive-content screen";
  if (source === "local_ocr_no_text") return "No readable text detected";
  if (source === "local_ocr_unclassified") return "Local OCR found no reliable document type";
  if (source === "local_ocr_provider_unconfigured" || source === "local_ocr_provider_fallback") return "Local OCR fallback";
  return source.replaceAll("_", " ");
}

function StatusPill({ status }: { status: string }) {
  const tone = status === "failed" ? "bg-red-100 text-red-800" : status === "needs_review" ? "bg-amber-100 text-amber-800" : status === "routed" ? "bg-emerald-100 text-emerald-800" : "bg-iron-100 text-iron-700";
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${tone}`}>{status.replaceAll("_", " ")}</span>;
}
