import { FormEvent, useState } from "react";

import { documentsApi, RFQAttachmentManifest } from "../api/documents";

export function RFQAttachmentManifestPanel() {
  const [documentIds, setDocumentIds] = useState("");
  const [manifest, setManifest] = useState<RFQAttachmentManifest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const ids = documentIds.split(/[\n, ]+/).map((item) => item.trim()).filter(Boolean);
    setIsLoading(true);
    setError(null);
    try {
      setManifest(await documentsApi.attachmentManifest(ids));
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to build attachment manifest");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <form className="rounded-md border border-iron-100 bg-white p-5" onSubmit={submit}>
      <div>
        <h2 className="text-base font-semibold text-iron-950">RFQ Attachment Manifest</h2>
        <p className="mt-1 text-sm text-iron-500">Paste document IDs to build a size/hash/status manifest for RFQ package attachments.</p>
      </div>
      <textarea value={documentIds} onChange={(event) => setDocumentIds(event.target.value)} className="mt-4 min-h-24 w-full rounded-md border border-iron-100 px-3 py-2 text-sm" placeholder="document-id-1&#10;document-id-2" />
      {error ? <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
      <button type="submit" disabled={isLoading} className="mt-4 rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white">{isLoading ? "Building..." : "Build manifest"}</button>
      {manifest ? (
        <div className="mt-4 space-y-3 text-sm text-iron-700">
          <div className="rounded-md border border-iron-100 p-3">{manifest.item_count} files / {manifest.total_size_bytes.toLocaleString()} bytes</div>
          {manifest.items.map((item) => <div key={item.document_id} className="rounded-md border border-iron-100 p-3"><div className="font-semibold text-iron-950">{item.title}</div><div>{item.category} / {item.status} / {item.filename ?? "no filename"}</div></div>)}
          {manifest.warnings.length ? <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-amber-800">{manifest.warnings.join(" ")}</div> : null}
        </div>
      ) : null}
    </form>
  );
}
