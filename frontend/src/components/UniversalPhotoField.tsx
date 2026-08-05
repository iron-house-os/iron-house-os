import {
  ArrowRight, Box, Camera, Crop, Download, Highlighter, History, Minus, Pencil,
  Plus, Redo2, RotateCw, Share2, Type, Upload, X,
} from "lucide-react";
import { PointerEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";

import { MediaAsset, MediaCategory, MediaOperation, mediaApi } from "../api/media";

type Props = {
  files?: File[];
  onFilesChange?: (files: File[]) => void;
  documentIds?: string[];
  category?: MediaCategory;
  label?: string;
  projectId?: string;
  recordType?: string;
  recordId?: string;
};

type Annotation = { type: "draw" | "arrow" | "box" | "highlight" | "text"; text?: string };

export function UniversalPhotoField({
  files = [],
  onFilesChange,
  documentIds = [],
  category = "job_photo",
  label = "Photos",
  projectId,
  recordType,
  recordId,
}: Props) {
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [recordFiles, setRecordFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const selectedFiles = onFilesChange ? files : recordFiles;
  const changeFiles = onFilesChange ?? setRecordFiles;
  const [active, setActive] = useState<MediaAsset | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!documentIds.length && !(recordType && recordId)) {
      setAssets([]);
      return;
    }
    let mounted = true;
    mediaApi.list(documentIds.length ? { documentIds } : { recordType, recordId }).then((items) => mounted && setAssets(items)).catch((reason) => {
      if (mounted) setError(reason instanceof Error ? reason.message : "Unable to load photos.");
    });
    return () => { mounted = false; };
  }, [documentIds.join(","), recordId, recordType]);

  const previews = useMemo(() => selectedFiles.map((file) => ({ file, url: URL.createObjectURL(file) })), [selectedFiles]);
  useEffect(() => () => previews.forEach((item) => URL.revokeObjectURL(item.url)), [previews]);

  async function uploadToRecord() {
    if (!recordId || !recordType || !selectedFiles.length) return;
    setUploading(true); setError(null); setProgress(0);
    try {
      const uploaded = await mediaApi.upload({ files: selectedFiles, projectId, category }, setProgress);
      const linked = await Promise.all(uploaded.map((asset) => mediaApi.link(asset.id, recordType, recordId)));
      setAssets((items) => [...linked, ...items]);
      changeFiles([]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Upload failed. Your selected photos were retained for retry.");
    } finally { setUploading(false); }
  }

  return (
    <div className="grid gap-2 text-sm">
      <span className="font-medium text-iron-700">{label}</span>
      {(onFilesChange || recordId) ? (
        <label className="flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-md border border-dashed border-brand-gold/60 bg-brand-gold/5 px-3 py-2 font-semibold text-iron-800">
          <Camera className="h-4 w-4" />
          {selectedFiles.length ? selectedFiles.length + " ready to upload" : "Take photos or choose multiple"}
          <input
            type="file"
            accept="image/*"
            multiple
            capture="environment"
            className="sr-only"
            onChange={(event) => changeFiles(Array.from(event.target.files ?? []))}
          />
        </label>
      ) : null}
      {previews.length ? (
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
          {previews.map(({ file, url }, index) => (
            <div key={file.name + file.lastModified} className="relative aspect-square overflow-hidden rounded-md border border-iron-100 bg-iron-50">
              <img src={url} alt={file.name} className="h-full w-full object-cover" />
              <button
                type="button"
                aria-label={"Remove " + file.name}
                onClick={() => changeFiles(selectedFiles.filter((_, itemIndex) => itemIndex !== index))}
                className="absolute right-1 top-1 rounded-full bg-iron-950/80 p-1 text-white"
              ><X className="h-3 w-3" /></button>
            </div>
          ))}
        </div>
      ) : null}
      {recordId && selectedFiles.length ? <button type="button" disabled={uploading} onClick={() => void uploadToRecord()} className="rounded-md bg-brand-gold px-3 py-2 font-semibold text-brand-black disabled:opacity-50">{uploading ? "Uploading " + progress + "%" : error ? "Retry upload" : "Upload photos"}</button> : null}
      {assets.length ? (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
          {assets.map((asset) => (
            <button
              type="button"
              key={asset.id}
              onClick={() => setActive(asset)}
              className="group overflow-hidden rounded-md border border-iron-100 bg-white text-left"
            >
              <img src={mediaApi.contentUrl(asset.id)} alt={asset.caption ?? asset.category} className="aspect-square w-full object-cover transition group-hover:scale-[1.02]" />
              <span className="block truncate px-2 py-1 text-xs text-iron-600">{asset.caption ?? asset.category.replaceAll("_", " ")}</span>
            </button>
          ))}
        </div>
      ) : null}
      {error ? <p role="alert" className="text-xs text-red-700">{error}</p> : null}
      {active ? <PhotoViewer asset={active} onClose={() => setActive(null)} onChange={(updated) => {
        setActive(updated);
        setAssets((items) => items.map((item) => item.id === updated.id ? updated : item));
      }} /> : null}
      <input type="hidden" value={category} readOnly />
    </div>
  );
}

function PhotoViewer({ asset, onClose, onChange }: { asset: MediaAsset; onClose: () => void; onChange: (asset: MediaAsset) => void }) {
  const imageRef = useRef<HTMLImageElement>(null);
  const [versionId, setVersionId] = useState(asset.current_version_id);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number } | null>(null);
  const [rotation, setRotation] = useState(0);
  const [straighten, setStraighten] = useState(0);
  const [cropInset, setCropInset] = useState(0);
  const [brightness, setBrightness] = useState(100);
  const [contrast, setContrast] = useState(100);
  const [clarity, setClarity] = useState(0);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [annotationText, setAnnotationText] = useState("Note");
  const [caption, setCaption] = useState(asset.caption ?? "");
  const [location, setLocation] = useState(asset.location ?? "");
  const [capturedDate, setCapturedDate] = useState(asset.captured_date ?? "");
  const [category, setCategory] = useState<MediaCategory>(asset.category);
  const [tab, setTab] = useState<"edit" | "history" | "metadata">("edit");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const currentVersion = asset.versions.find((version) => version.id === versionId) ?? asset.versions[0];

  function pointerDown(event: PointerEvent<HTMLDivElement>) {
    drag.current = { x: event.clientX - pan.x, y: event.clientY - pan.y };
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function pointerMove(event: PointerEvent<HTMLDivElement>) {
    if (drag.current) setPan({ x: event.clientX - drag.current.x, y: event.clientY - drag.current.y });
  }

  function operations(): MediaOperation[] {
    const result: MediaOperation[] = [];
    if (rotation) result.push({ type: "rotate", values: { degrees: rotation } });
    if (straighten) result.push({ type: "straighten", values: { degrees: straighten } });
    if (cropInset) result.push({ type: "crop", values: { x: cropInset, y: cropInset, width: 100 - cropInset * 2, height: 100 - cropInset * 2 } });
    if (brightness !== 100) result.push({ type: "brightness", values: { percent: brightness } });
    if (contrast !== 100) result.push({ type: "contrast", values: { percent: contrast } });
    if (clarity) result.push({ type: "clarity", values: { percent: clarity } });
    annotations.forEach((item) => result.push({ type: item.type, values: item.text ? { text: item.text } : {} }));
    return result;
  }

  async function renderEdit(): Promise<Blob> {
    const image = imageRef.current;
    if (!image?.naturalWidth) throw new Error("Photo is still loading.");
    const radians = ((rotation + straighten) * Math.PI) / 180;
    const insetX = image.naturalWidth * cropInset / 100;
    const insetY = image.naturalHeight * cropInset / 100;
    const sourceWidth = image.naturalWidth - insetX * 2;
    const sourceHeight = image.naturalHeight - insetY * 2;
    const swap = Math.abs(rotation) % 180 === 90;
    const canvas = document.createElement("canvas");
    canvas.width = swap ? sourceHeight : sourceWidth;
    canvas.height = swap ? sourceWidth : sourceHeight;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("This browser cannot edit photos.");
    context.filter = "brightness(" + brightness + "%) contrast(" + contrast + "%) saturate(" + (100 + clarity / 2) + "%)";
    context.translate(canvas.width / 2, canvas.height / 2);
    context.rotate(radians);
    context.drawImage(image, insetX, insetY, sourceWidth, sourceHeight, -sourceWidth / 2, -sourceHeight / 2, sourceWidth, sourceHeight);
    context.setTransform(1, 0, 0, 1, 0, 0);
    context.filter = "none";
    annotations.forEach((annotation, index) => drawAnnotation(context, canvas, annotation, index));
    return new Promise((resolve, reject) => canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error("Unable to create edited photo.")), "image/png"));
  }

  async function saveEdit() {
    const editOperations = operations();
    if (!editOperations.length) return;
    setSaving(true); setError(null);
    try {
      const updated = await mediaApi.addVersion(asset.id, await renderEdit(), {
        action: "edit",
        operations: editOperations,
        changeSummary: "Photo correction and annotation",
      });
      onChange(updated);
      setVersionId(updated.current_version_id);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to save photo version."); }
    finally { setSaving(false); }
  }

  async function saveMetadata() {
    setSaving(true); setError(null);
    try {
      onChange(await mediaApi.updateMetadata(asset.id, { caption, captured_date: capturedDate || null, location: location || null, category }));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to save metadata."); }
    finally { setSaving(false); }
  }

  async function restore(targetId: string) {
    const reason = asset.controlled ? window.prompt("Reason for controlled amendment") ?? "" : undefined;
    if (asset.controlled && !reason) return;
    setSaving(true); setError(null);
    try {
      const updated = await mediaApi.restore(asset.id, targetId, reason);
      onChange(updated);
      setVersionId(updated.current_version_id);
    }
    catch (failure) { setError(failure instanceof Error ? failure.message : "Unable to restore version."); }
    finally { setSaving(false); }
  }

  async function replace(file: File) {
    const reason = asset.controlled ? window.prompt("Reason for controlled replacement") ?? "" : undefined;
    if (asset.controlled && !reason) return;
    setSaving(true); setError(null);
    try {
      const updated = await mediaApi.addVersion(asset.id, file, {
        action: "replacement", operations: [], changeSummary: "Incorrect upload replaced", amendmentReason: reason,
      });
      onChange(updated);
      setVersionId(updated.current_version_id);
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Unable to replace photo."); }
    finally { setSaving(false); }
  }

  return (
    <div role="dialog" aria-modal="true" aria-label="Photo viewer and editor" className="fixed inset-0 z-[100] flex flex-col bg-iron-950 text-white">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 px-3 py-2">
        <div><div className="font-semibold">{asset.caption ?? "Photo evidence"}</div><div className="text-xs text-iron-100">Version {currentVersion?.version_number} · original always retained</div></div>
        <div className="flex gap-2">
          <a href={mediaApi.contentUrl(asset.id, versionId, true)} className="rounded-md border border-white/20 p-2" aria-label="Download permitted photo"><Download className="h-4 w-4" /></a>
          {navigator.share ? <button type="button" onClick={() => void navigator.share({ title: asset.caption ?? "IHOS photo evidence", url: mediaApi.contentUrl(asset.id, versionId) })} className="rounded-md border border-white/20 p-2" aria-label="Share permitted photo"><Share2 className="h-4 w-4" /></button> : null}
          <button type="button" onClick={onClose} className="rounded-md border border-white/20 p-2" aria-label="Close viewer"><X className="h-4 w-4" /></button>
        </div>
      </header>
      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <div
          className="relative min-h-[40vh] flex-1 touch-none overflow-hidden bg-black"
          onPointerDown={pointerDown}
          onPointerMove={pointerMove}
          onPointerUp={() => { drag.current = null; }}
        >
          <img
            ref={imageRef}
            crossOrigin="use-credentials"
            src={mediaApi.contentUrl(asset.id, versionId)}
            alt={asset.caption ?? "Photo evidence"}
            draggable={false}
            className="absolute left-1/2 top-1/2 max-h-full max-w-full select-none object-contain"
            style={{
              filter: "brightness(" + brightness + "%) contrast(" + contrast + "%) saturate(" + (100 + clarity / 2) + "%)",
              clipPath: cropInset ? "inset(" + cropInset + "%)" : undefined,
              transform: "translate(calc(-50% + " + pan.x + "px), calc(-50% + " + pan.y + "px)) scale(" + zoom + ") rotate(" + (rotation + straighten) + "deg)",
            }}
          />
          <div className="absolute bottom-3 left-3 flex gap-1 rounded-md bg-black/70 p-1">
            <button type="button" onClick={() => setZoom(Math.max(0.5, zoom - 0.25))} className="p-2" aria-label="Zoom out"><Minus className="h-4 w-4" /></button>
            <span className="min-w-12 py-2 text-center text-xs">{Math.round(zoom * 100)}%</span>
            <button type="button" onClick={() => setZoom(Math.min(4, zoom + 0.25))} className="p-2" aria-label="Zoom in"><Plus className="h-4 w-4" /></button>
          </div>
        </div>
        <aside className="w-full overflow-y-auto border-l border-white/10 bg-iron-950 p-3 lg:w-96">
          <div className="grid grid-cols-3 gap-1 rounded-md bg-white/5 p-1">
            {(["edit", "metadata", "history"] as const).map((item) => <button type="button" key={item} onClick={() => setTab(item)} className={"rounded px-2 py-2 text-xs font-semibold capitalize " + (tab === item ? "bg-brand-gold text-brand-black" : "")}>{item}</button>)}
          </div>
          {tab === "edit" ? (
            <div className="mt-4 grid gap-4">
              <div className="grid grid-cols-3 gap-2">
                <Tool icon={<RotateCw />} label="Rotate" onClick={() => setRotation((rotation + 90) % 360)} />
                <Tool icon={<Redo2 />} label="Straighten" onClick={() => setStraighten(straighten === 2 ? 0 : 2)} />
                <Tool icon={<Crop />} label="Crop" onClick={() => setCropInset(cropInset ? 0 : 5)} />
              </div>
              <Range label="Brightness" value={brightness} min={50} max={150} onChange={setBrightness} />
              <Range label="Contrast" value={contrast} min={50} max={150} onChange={setContrast} />
              <Range label="Clarity" value={clarity} min={0} max={100} onChange={setClarity} />
              <div>
                <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-iron-100">Annotations</div>
                <div className="grid grid-cols-5 gap-1">
                  <Tool icon={<Pencil />} label="Draw" onClick={() => setAnnotations([...annotations, { type: "draw" }])} />
                  <Tool icon={<ArrowRight />} label="Arrow" onClick={() => setAnnotations([...annotations, { type: "arrow" }])} />
                  <Tool icon={<Box />} label="Box" onClick={() => setAnnotations([...annotations, { type: "box" }])} />
                  <Tool icon={<Highlighter />} label="Highlight" onClick={() => setAnnotations([...annotations, { type: "highlight" }])} />
                  <Tool icon={<Type />} label="Text" onClick={() => setAnnotations([...annotations, { type: "text", text: annotationText }])} />
                </div>
                <input value={annotationText} onChange={(event) => setAnnotationText(event.target.value)} className="mt-2 w-full rounded border border-white/20 bg-black px-3 py-2 text-sm" aria-label="Annotation text" />
              </div>
              <button type="button" disabled={saving || !operations().length} onClick={() => void saveEdit()} className="rounded-md bg-brand-gold px-4 py-2 font-semibold text-brand-black disabled:opacity-50">{saving ? "Saving version…" : "Save as new version"}</button>
              <label className="flex cursor-pointer items-center justify-center gap-2 rounded-md border border-white/20 px-3 py-2 text-sm font-semibold"><Upload className="h-4 w-4" />Replace incorrect upload<input type="file" accept="image/*" className="sr-only" onChange={(event) => { const file = event.target.files?.[0]; if (file) void replace(file); }} /></label>
            </div>
          ) : null}
          {tab === "metadata" ? (
            <div className="mt-4 grid gap-3">
              <Field label="Caption" value={caption} onChange={setCaption} />
              <Field label="Photo date" value={capturedDate} onChange={setCapturedDate} type="date" />
              <div className="text-xs text-iron-100">Project: {asset.project_id ?? "Not linked"}</div>
              <Field label="Location (restricted)" value={location} onChange={setLocation} />
              <label className="grid gap-1 text-sm"><span>Category</span><select value={category} onChange={(event) => setCategory(event.target.value as MediaCategory)} className="rounded border border-white/20 bg-black px-3 py-2">{["job_photo","production_photo","inspection","equipment","flha","incident","deficiency","expense","receipt","backup"].map((item) => <option key={item}>{item}</option>)}</select></label>
              <button type="button" disabled={saving} onClick={() => void saveMetadata()} className="rounded-md bg-brand-gold px-4 py-2 font-semibold text-brand-black">Save metadata version</button>
            </div>
          ) : null}
          {tab === "history" ? (
            <div className="mt-4 grid gap-2">
              {asset.versions.map((version) => (
                <article key={version.id} className={"rounded-md border p-3 " + (version.id === asset.current_version_id ? "border-brand-gold" : "border-white/10")}>
                  <button type="button" onClick={() => setVersionId(version.id)} className="w-full text-left">
                    <div className="flex items-center justify-between"><span className="font-semibold">Version {version.version_number}</span><span className="text-xs capitalize text-iron-100">{version.action}</span></div>
                    <div className="mt-1 text-xs text-iron-100">{version.editor_email} · {new Date(version.created_at).toLocaleString()}</div>
                    <div className="mt-1 text-xs">{version.change_summary}</div>
                  </button>
                  {version.id !== asset.current_version_id ? <button type="button" disabled={saving} onClick={() => void restore(version.id)} className="mt-2 flex items-center gap-1 text-xs font-semibold text-brand-gold"><History className="h-3 w-3" />Restore as new version</button> : null}
                </article>
              ))}
            </div>
          ) : null}
          {error ? <p role="alert" className="mt-3 rounded bg-red-950 p-2 text-sm">{error}</p> : null}
        </aside>
      </div>
    </div>
  );
}

function drawAnnotation(context: CanvasRenderingContext2D, canvas: HTMLCanvasElement, annotation: Annotation, index: number) {
  const offset = index * 18;
  context.lineWidth = Math.max(3, canvas.width / 250);
  context.strokeStyle = "#f4b41a";
  context.fillStyle = "#f4b41a";
  context.font = "bold " + Math.max(18, canvas.width / 30) + "px sans-serif";
  if (annotation.type === "draw") { context.beginPath(); context.moveTo(canvas.width * .2, canvas.height * .7 - offset); context.lineTo(canvas.width * .75, canvas.height * .3 - offset); context.stroke(); }
  if (annotation.type === "arrow") { context.beginPath(); context.moveTo(canvas.width * .2, canvas.height * .5); context.lineTo(canvas.width * .75, canvas.height * .5); context.lineTo(canvas.width * .68, canvas.height * .43); context.moveTo(canvas.width * .75, canvas.height * .5); context.lineTo(canvas.width * .68, canvas.height * .57); context.stroke(); }
  if (annotation.type === "box") context.strokeRect(canvas.width * .2 + offset, canvas.height * .2 + offset, canvas.width * .5, canvas.height * .45);
  if (annotation.type === "highlight") { context.save(); context.globalAlpha = .3; context.fillRect(canvas.width * .15, canvas.height * .42 + offset, canvas.width * .7, canvas.height * .15); context.restore(); }
  if (annotation.type === "text") context.fillText(annotation.text ?? "Note", canvas.width * .15, canvas.height * .2 + offset);
}

function Tool({ icon, label, onClick }: { icon: ReactNode; label: string; onClick: () => void }) {
  return <button type="button" onClick={onClick} title={label} className="flex min-h-12 flex-col items-center justify-center gap-1 rounded border border-white/10 p-1 text-[10px]">{icon}{label}</button>;
}
function Range({ label, value, min, max, onChange }: { label: string; value: number; min: number; max: number; onChange: (value: number) => void }) {
  return <label className="grid gap-1 text-xs"><span className="flex justify-between"><span>{label}</span><span>{value}</span></span><input type="range" min={min} max={max} value={value} onChange={(event) => onChange(Number(event.target.value))} /></label>;
}
function Field({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return <label className="grid gap-1 text-sm"><span>{label}</span><input type={type} value={value} onChange={(event) => onChange(event.target.value)} className="rounded border border-white/20 bg-black px-3 py-2" /></label>;
}
