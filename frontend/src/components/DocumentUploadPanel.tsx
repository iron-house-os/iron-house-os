import { FormEvent, useState } from "react";

import { documentCategories, DocumentCategory, DocumentUploadResponse, documentsApi } from "../api/documents";

type Props = {
  projectId?: string | null;
  onUploaded?: (upload: DocumentUploadResponse) => void;
};

export function DocumentUploadPanel({ projectId, onUploaded }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState<DocumentCategory>("drawing");
  const [revision, setRevision] = useState("");
  const [description, setDescription] = useState("");
  const [upload, setUpload] = useState<DocumentUploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Choose a file before uploading.");
      return;
    }
    setIsUploading(true);
    setError(null);
    try {
      const response = await documentsApi.upload({
        file,
        title: title || undefined,
        category,
        project_id: projectId || undefined,
        description: description || undefined,
        revision: revision || undefined,
      });
      setUpload(response);
      onUploaded?.(response);
      setFile(null);
      setTitle("");
      setRevision("");
      setDescription("");
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to upload document");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <form className="rounded-md border border-iron-100 bg-white p-5" onSubmit={submit}>
      <div>
        <h2 className="text-base font-semibold text-iron-950">Upload Document</h2>
        <p className="mt-1 text-sm text-iron-500">Upload drawings, specs, addenda, quotes, or supporting files and attach them to a project.</p>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <label className="grid gap-1 text-sm xl:col-span-2">
          <span className="font-medium text-iron-700">File</span>
          <input type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} className="rounded-md border border-iron-100 px-3 py-2" />
        </label>
        <label className="grid gap-1 text-sm">
          <span className="font-medium text-iron-700">Title</span>
          <input value={title} onChange={(event) => setTitle(event.target.value)} className="rounded-md border border-iron-100 px-3 py-2" />
        </label>
        <label className="grid gap-1 text-sm">
          <span className="font-medium text-iron-700">Category</span>
          <select value={category} onChange={(event) => setCategory(event.target.value as DocumentCategory)} className="rounded-md border border-iron-100 px-3 py-2">
            {documentCategories.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label className="grid gap-1 text-sm">
          <span className="font-medium text-iron-700">Revision</span>
          <input value={revision} onChange={(event) => setRevision(event.target.value)} className="rounded-md border border-iron-100 px-3 py-2" />
        </label>
        <label className="grid gap-1 text-sm xl:col-span-5">
          <span className="font-medium text-iron-700">Description</span>
          <input value={description} onChange={(event) => setDescription(event.target.value)} className="rounded-md border border-iron-100 px-3 py-2" />
        </label>
      </div>
      {error ? <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
      {upload ? <div className="mt-4 rounded-md border border-iron-100 p-3 text-sm text-iron-700">Uploaded {upload.original_filename} ({upload.size_bytes.toLocaleString()} bytes). Duplicates: {upload.duplicate_document_ids.length}</div> : null}
      <button type="submit" disabled={isUploading} className="mt-4 rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white">
        {isUploading ? "Uploading..." : "Upload"}
      </button>
    </form>
  );
}
