import { useState } from "react";

import { DocumentList, DocumentStatus, documentsApi, LibraryDocument } from "../api/documents";

type Props = {
  projectId?: string | null;
};

export function ProjectDocumentBrowser({ projectId }: Props) {
  const [documents, setDocuments] = useState<DocumentList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function loadDocuments() {
    setIsLoading(true);
    setError(null);
    try {
      setDocuments(await documentsApi.list({ project_id: projectId || undefined }));
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to load documents");
    } finally {
      setIsLoading(false);
    }
  }

  async function setStatus(document: LibraryDocument, status: DocumentStatus) {
    await documentsApi.updateStatus(document.id, status);
    await loadDocuments();
  }

  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-base font-semibold text-iron-950">Project Document Browser</h2>
          <p className="mt-1 text-sm text-iron-500">Load uploaded documents, download stored files, and mark records current or superseded.</p>
        </div>
        <button type="button" onClick={loadDocuments} disabled={isLoading} className="rounded-md border border-iron-100 px-4 py-2 text-sm font-semibold text-iron-800">
          {isLoading ? "Loading..." : "Load documents"}
        </button>
      </div>
      {error ? <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
      {documents ? (
        <div className="mt-4 overflow-hidden rounded-md border border-iron-100">
          <table className="w-full text-left text-sm">
            <thead className="bg-iron-50 text-xs uppercase tracking-wide text-iron-500">
              <tr><th className="px-3 py-2">Title</th><th className="px-3 py-2">Category</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Revision</th><th className="px-3 py-2">Actions</th></tr>
            </thead>
            <tbody>
              {documents.items.map((document) => (
                <tr key={document.id} className="border-t border-iron-100">
                  <td className="px-3 py-2 font-medium text-iron-950">{document.title}</td>
                  <td className="px-3 py-2 text-iron-700">{document.category}</td>
                  <td className="px-3 py-2 text-iron-700">{document.status}</td>
                  <td className="px-3 py-2 text-iron-700">{document.drawing?.revision ?? "-"}</td>
                  <td className="space-x-2 px-3 py-2 text-iron-700">
                    {document.storage_uri ? <a className="font-semibold" href={documentsApi.downloadUrl(document.id)}>Download</a> : null}
                    <button type="button" className="font-semibold" onClick={() => void setStatus(document, "current")}>Current</button>
                    <button type="button" className="font-semibold" onClick={() => void setStatus(document, "superseded")}>Supersede</button>
                  </td>
                </tr>
              ))}
              {documents.items.length === 0 ? <tr><td className="px-3 py-3 text-iron-500" colSpan={5}>No documents found.</td></tr> : null}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
