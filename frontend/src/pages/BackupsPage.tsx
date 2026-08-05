import { Camera, Inbox, RefreshCw, ShieldAlert } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { BackupIntake, backupsApi } from "../api/backups";
import { mediaApi } from "../api/media";
import { useAuth } from "../contexts/AuthContext";

export function BackupsPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<BackupIntake[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [note, setNote] = useState("");
  const [projectHint, setProjectHint] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const management = ["admin", "operations_manager"].includes(user?.role ?? "");

  const load = useCallback(async () => {
    try {
      const response = await backupsApi.list();
      setItems(response.items);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load Backups.");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);
  const preview = useMemo(() => file ? URL.createObjectURL(file) : null, [file]);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file) { setError("Choose one photo first."); return; }
    setBusy(true); setError(null); setMessage(null);
    try {
      const intake = await backupsApi.upload(file, note.trim() || undefined, projectHint.trim() || undefined);
      setItems((current) => [intake, ...current.filter((item) => item.id !== intake.id)]);
      setFile(null); setNote(""); setProjectHint("");
      setMessage("Original saved. The daily controller will route a review-only record.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Upload failed; your selected photo is still available to retry.");
    } finally { setBusy(false); }
  }

  async function runController() {
    setBusy(true); setError(null); setMessage(null);
    try {
      const result = await backupsApi.runDaily();
      setMessage(`Controller checked ${result.selected}: ${result.routed} routed, ${result.needs_review} triage, ${result.failed} failed.`);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Controller run failed.");
    } finally { setBusy(false); }
  }

  return (
    <div className="space-y-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-gold">Administration · document intake</p>
        <h1 className="mt-1 text-2xl font-semibold text-iron-950">Backups</h1>
        <p className="mt-2 max-w-3xl text-sm text-iron-600">Save one immutable photo now. Daily classification only creates unapproved records for human review.</p>
      </header>

      <section className="grid gap-5 rounded-xl border border-iron-100 bg-white p-5 shadow-sm lg:grid-cols-[minmax(0,1fr)_minmax(18rem,0.7fr)]" aria-labelledby="backup-upload-title">
        <form className="space-y-4" onSubmit={(event) => void submit(event)}>
          <div><h2 id="backup-upload-title" className="font-semibold text-iron-900">Send one photo</h2><p className="text-sm text-iron-500">Camera images and uploaded image files are accepted one at a time.</p></div>
          <label className="flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-md border border-dashed border-brand-gold/60 bg-brand-gold/5 px-3 py-3 font-semibold text-iron-800">
            <Camera className="h-4 w-4" aria-hidden="true" />
            {file ? file.name : "Take photo or choose image"}
            <input className="sr-only" type="file" accept="image/*" capture="environment" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
          </label>
          <label className="grid gap-1 text-sm font-medium text-iron-700">Optional note<textarea className="min-h-20 rounded-md border border-iron-200 px-3 py-2" maxLength={2000} value={note} onChange={(event) => setNote(event.target.value)} /></label>
          <label className="grid gap-1 text-sm font-medium text-iron-700">Optional project hint<input className="rounded-md border border-iron-200 px-3 py-2" maxLength={255} value={projectHint} onChange={(event) => setProjectHint(event.target.value)} placeholder="Text hint only — no automatic project selection" /></label>
          <button type="submit" disabled={!file || busy} className="rounded-md bg-brand-gold px-4 py-2 font-semibold text-brand-black disabled:opacity-50">{busy ? "Working…" : "Save original"}</button>
        </form>
        <div className="grid min-h-48 place-items-center overflow-hidden rounded-lg bg-iron-50">
          {preview ? <img src={preview} alt="Selected Backups photo preview" className="max-h-80 w-full object-contain" /> : <div className="text-center text-sm text-iron-400"><Inbox className="mx-auto mb-2 h-8 w-8" /><span>No photo selected</span></div>}
        </div>
      </section>

      {message ? <p role="status" className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{message}</p> : null}
      {error ? <p role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}

      <section className="space-y-3" aria-labelledby="backup-queue-title">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><h2 id="backup-queue-title" className="text-lg font-semibold text-iron-900">{management ? "Company queue" : "My submissions"}</h2><p className="text-sm text-iron-500">Originals remain private to the submitter and management.</p></div>
          {management ? <button type="button" disabled={busy} onClick={() => void runController()} className="flex items-center gap-2 rounded-md border border-iron-200 bg-white px-3 py-2 text-sm font-semibold text-iron-800"><RefreshCw className="h-4 w-4" />Run daily controller</button> : null}
        </div>
        {!items.length ? <div className="rounded-lg border border-dashed border-iron-200 bg-white p-6 text-center text-sm text-iron-500">No Backups submissions yet.</div> : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{items.map((item) => <BackupCard key={item.id} item={item} showUploader={management} />)}</div>
        )}
      </section>
    </div>
  );
}

function BackupCard({ item, showUploader }: { item: BackupIntake; showUploader: boolean }) {
  return <article className="overflow-hidden rounded-lg border border-iron-100 bg-white shadow-sm">
    <img src={mediaApi.contentUrl(item.media_asset_id)} alt={item.note ?? "Backups original"} className="aspect-[4/3] w-full bg-iron-50 object-cover" />
    <div className="space-y-2 p-4 text-sm">
      <div className="flex items-center justify-between gap-2"><span className="font-semibold capitalize text-iron-900">{item.status.replaceAll("_", " ")}</span>{item.sensitive_quarantine ? <span className="flex items-center gap-1 text-xs font-semibold text-red-700"><ShieldAlert className="h-3 w-3" />Quarantined</span> : null}</div>
      {showUploader ? <p className="truncate text-xs text-iron-500">{item.uploader_email} · {item.uploader_role.replaceAll("_", " ")}</p> : null}
      <p className="text-iron-700">{item.note ?? "No note"}</p>
      {item.project_hint ? <p className="text-xs text-iron-500">Project hint: {item.project_hint}</p> : null}
      <p className="text-xs text-iron-500">{item.detected_type ? `Detected ${item.detected_type.replaceAll("_", " ")}${item.confidence === null ? "" : ` · ${Math.round(item.confidence * 100)}%`}` : "Waiting for daily controller"}</p>
      {item.error ? <p className="text-xs text-amber-700">{item.error}</p> : null}
      <p className="text-[11px] text-iron-400">Uploaded {new Date(item.uploaded_at).toLocaleString()}</p>
    </div>
  </article>;
}
