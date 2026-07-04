import { BookOpen, FilePlus2, RefreshCw, Save } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  DocumentCategory,
  DocumentCreatePayload,
  DocumentStatus,
  LibraryDocument,
  documentCategories,
  documentStatuses,
  documentsApi,
} from "../api/documents";

export function DocumentLibraryPage() {
  const { documentId } = useParams();
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<LibraryDocument[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<LibraryDocument | null>(null);
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const list = await documentsApi.list({ category, status });
      setDocuments(list.items);
      if (documentId) {
        setSelectedDocument(await documentsApi.detail(documentId));
      } else {
        setSelectedDocument(null);
      }
    } catch (currentError) {
      setError(
        currentError instanceof Error ? currentError.message : "Unable to load documents",
      );
    } finally {
      setIsLoading(false);
    }
  }, [category, documentId, status]);

  useEffect(() => {
    // This effect keeps the library aligned with route selection and active filters.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, [refresh]);

  async function createDocument(payload: DocumentCreatePayload) {
    const created = await documentsApi.create(payload);
    navigate(`/documents/${created.id}`);
  }

  async function updateStatus(nextStatus: DocumentStatus) {
    if (!selectedDocument) return;
    await documentsApi.updateStatus(selectedDocument.id, nextStatus);
    await refresh();
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-iron-100 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-iron-950">Document Library</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
            Register metadata for drawings, specifications, addenda, project records, RFQ
            attachments, and future storage sync.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          className="inline-flex items-center gap-2 rounded-md border border-iron-100 bg-white px-3 py-2 text-sm font-medium text-iron-800"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {error ? <Notice tone="error" message={error} /> : null}
      {isLoading ? <Notice tone="neutral" message="Loading documents..." /> : null}

      <div className="grid gap-6 xl:grid-cols-[440px_1fr]">
        <div className="space-y-6">
          <DocumentFilters
            category={category}
            status={status}
            onCategoryChange={setCategory}
            onStatusChange={setStatus}
          />
          <CreateDocumentForm onSubmit={(payload) => void createDocument(payload)} />
          <DocumentTable documents={documents} selectedId={documentId} />
        </div>

        {selectedDocument ? (
          <DocumentDetail document={selectedDocument} onStatusChange={(value) => void updateStatus(value)} />
        ) : (
          <div className="rounded-md border border-iron-100 bg-white p-6">
            <h2 className="text-base font-semibold text-iron-950">No document selected</h2>
            <p className="mt-2 text-sm leading-6 text-iron-500">
              Register or select a document to review storage, links, and drawing metadata.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

function DocumentFilters({
  category,
  status,
  onCategoryChange,
  onStatusChange,
}: {
  category: string;
  status: string;
  onCategoryChange: (value: string) => void;
  onStatusChange: (value: string) => void;
}) {
  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <h2 className="text-base font-semibold text-iron-950">Filters</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <select
          value={category}
          onChange={(event) => onCategoryChange(event.target.value)}
          className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
        >
          <option value="">All categories</option>
          {documentCategories.map((item) => (
            <option key={item} value={item}>
              {label(item)}
            </option>
          ))}
        </select>
        <select
          value={status}
          onChange={(event) => onStatusChange(event.target.value)}
          className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
        >
          <option value="">All statuses</option>
          {documentStatuses.map((item) => (
            <option key={item} value={item}>
              {label(item)}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

function CreateDocumentForm({ onSubmit }: { onSubmit: (payload: DocumentCreatePayload) => void }) {
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState<DocumentCategory>("drawing");
  const [storageUri, setStorageUri] = useState("");
  const [rfqPackageId, setRfqPackageId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [sheetNumber, setSheetNumber] = useState("");
  const [drawingTitle, setDrawingTitle] = useState("");
  const [discipline, setDiscipline] = useState("civil");
  const [revision, setRevision] = useState("");
  const [issueDate, setIssueDate] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim()) return;
    const payload: DocumentCreatePayload = {
      title: title.trim(),
      category,
      storage_uri: storageUri.trim() || undefined,
      rfq_package_id: rfqPackageId.trim() || undefined,
      project_id: projectId.trim() || undefined,
      metadata: { source: "manual registration" },
    };
    if (category === "drawing") {
      payload.drawing = {
        sheet_number: sheetNumber.trim() || null,
        title: drawingTitle.trim() || title.trim(),
        discipline: discipline.trim() || null,
        revision: revision.trim() || null,
        issue_date: issueDate || null,
        storage_uri: storageUri.trim() || null,
      };
    }
    onSubmit(payload);
    setTitle("");
    setStorageUri("");
    setRfqPackageId("");
    setProjectId("");
    setSheetNumber("");
    setDrawingTitle("");
    setRevision("");
    setIssueDate("");
  }

  return (
    <form className="rounded-md border border-iron-100 bg-white p-5" onSubmit={handleSubmit}>
      <div className="mb-4 flex items-center gap-2">
        <FilePlus2 className="h-5 w-5 text-signal-blue" />
        <h2 className="text-base font-semibold text-iron-950">Register Document</h2>
      </div>
      <div className="space-y-3">
        <Field label="Document title">
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            placeholder="C-101 Utility Plan"
          />
        </Field>
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Category">
            <select
              value={category}
              onChange={(event) => setCategory(event.target.value as DocumentCategory)}
              className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            >
              {documentCategories.map((item) => (
                <option key={item} value={item}>
                  {label(item)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Storage URI">
            <input
              value={storageUri}
              onChange={(event) => setStorageUri(event.target.value)}
              className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
              placeholder="drive://future/path.pdf"
            />
          </Field>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Project ID">
            <input
              value={projectId}
              onChange={(event) => setProjectId(event.target.value)}
              className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            />
          </Field>
          <Field label="RFQ package ID">
            <input
              value={rfqPackageId}
              onChange={(event) => setRfqPackageId(event.target.value)}
              className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            />
          </Field>
        </div>
        {category === "drawing" ? (
          <div className="rounded-md border border-iron-100 bg-iron-50 p-4">
            <h3 className="text-sm font-semibold text-iron-950">Drawing metadata</h3>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <input
                value={sheetNumber}
                onChange={(event) => setSheetNumber(event.target.value)}
                className="rounded-md border border-iron-100 px-3 py-2 text-sm"
                placeholder="Sheet number"
              />
              <input
                value={drawingTitle}
                onChange={(event) => setDrawingTitle(event.target.value)}
                className="rounded-md border border-iron-100 px-3 py-2 text-sm"
                placeholder="Drawing title"
              />
              <input
                value={discipline}
                onChange={(event) => setDiscipline(event.target.value)}
                className="rounded-md border border-iron-100 px-3 py-2 text-sm"
                placeholder="Discipline"
              />
              <input
                value={revision}
                onChange={(event) => setRevision(event.target.value)}
                className="rounded-md border border-iron-100 px-3 py-2 text-sm"
                placeholder="Revision"
              />
              <input
                type="date"
                value={issueDate}
                onChange={(event) => setIssueDate(event.target.value)}
                className="rounded-md border border-iron-100 px-3 py-2 text-sm"
              />
            </div>
          </div>
        ) : null}
      </div>
      <button
        type="submit"
        className="mt-5 inline-flex items-center gap-2 rounded-md bg-iron-950 px-3 py-2 text-sm font-semibold text-white"
      >
        <BookOpen className="h-4 w-4" />
        Register
      </button>
    </form>
  );
}

function DocumentTable({
  documents,
  selectedId,
}: {
  documents: LibraryDocument[];
  selectedId: string | undefined;
}) {
  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <h2 className="text-base font-semibold text-iron-950">Documents</h2>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-iron-100 text-xs uppercase tracking-wide text-iron-500">
              <th className="py-2 pr-4">Title</th>
              <th className="py-2 pr-4">Category</th>
              <th className="py-2 pr-4">Status</th>
              <th className="py-2 pr-4">Belongs To</th>
            </tr>
          </thead>
          <tbody>
            {documents.length === 0 ? (
              <tr>
                <td className="py-3 text-iron-500" colSpan={4}>
                  No documents registered.
                </td>
              </tr>
            ) : (
              documents.map((document) => (
                <tr
                  key={document.id}
                  className={[
                    "border-b border-iron-100 last:border-b-0",
                    selectedId === document.id ? "bg-iron-50" : "",
                  ].join(" ")}
                >
                  <td className="py-3 pr-4 font-medium text-iron-950">
                    <Link to={`/documents/${document.id}`}>{document.title}</Link>
                  </td>
                  <td className="py-3 pr-4 text-iron-800">{label(document.category)}</td>
                  <td className="py-3 pr-4 text-iron-800">{label(document.status)}</td>
                  <td className="py-3 pr-4 text-iron-800">{belongsTo(document)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DocumentDetail({
  document,
  onStatusChange,
}: {
  document: LibraryDocument;
  onStatusChange: (status: DocumentStatus) => void;
}) {
  return (
    <div className="space-y-6">
      <div className="rounded-md border border-iron-100 bg-white p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="text-xs uppercase tracking-wide text-iron-500">
              {label(document.category)}
            </div>
            <h2 className="mt-1 text-2xl font-semibold text-iron-950">{document.title}</h2>
            <p className="mt-2 text-sm leading-6 text-iron-500">
              {document.description ?? "Metadata-only document record."}
            </p>
          </div>
          <select
            value={document.status}
            onChange={(event) => onStatusChange(event.target.value as DocumentStatus)}
            className="rounded-md border border-iron-100 bg-white px-3 py-2 text-sm"
          >
            {documentStatuses.map((item) => (
              <option key={item} value={item}>
                {label(item)}
              </option>
            ))}
          </select>
        </div>
        <dl className="mt-5 grid gap-4 md:grid-cols-3">
          <InfoTile label="Storage URI" value={document.storage_uri ?? "Not registered"} />
          <InfoTile label="Belongs to" value={belongsTo(document)} />
          <InfoTile label="Supplier" value={document.supplier_id ?? "Not supplier-specific"} />
        </dl>
      </div>
      <DrawingPanel document={document} />
    </div>
  );
}

function DrawingPanel({ document }: { document: LibraryDocument }) {
  if (document.category !== "drawing") {
    return (
      <div className="rounded-md border border-iron-100 bg-white p-5">
        <h2 className="text-base font-semibold text-iron-950">Drawing Metadata</h2>
        <p className="mt-2 text-sm text-iron-500">This document is not categorized as a drawing.</p>
      </div>
    );
  }
  const drawing = document.drawing;
  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div className="mb-4 flex items-center gap-2">
        <Save className="h-5 w-5 text-signal-blue" />
        <h2 className="text-base font-semibold text-iron-950">Drawing Metadata</h2>
      </div>
      <dl className="grid gap-4 md:grid-cols-3">
        <InfoTile label="Sheet" value={drawing?.sheet_number ?? "Not set"} />
        <InfoTile label="Drawing title" value={drawing?.title ?? "Not set"} />
        <InfoTile label="Discipline" value={drawing?.discipline ?? "Not set"} />
        <InfoTile label="Revision" value={drawing?.revision ?? "Not set"} />
        <InfoTile label="Issue date" value={drawing?.issue_date ?? "Not set"} />
        <InfoTile label="Storage URI" value={drawing?.storage_uri ?? "Not set"} />
      </dl>
    </div>
  );
}

function InfoTile({ label: itemLabel, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-iron-100 bg-iron-50 p-3">
      <dt className="text-xs uppercase tracking-wide text-iron-500">{itemLabel}</dt>
      <dd className="mt-1 break-words text-sm font-semibold text-iron-950">{value}</dd>
    </div>
  );
}

function Field({ label: itemLabel, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-iron-800">{itemLabel}</span>
      {children}
    </label>
  );
}

function Notice({ tone, message }: { tone: "neutral" | "error"; message: string }) {
  const className =
    tone === "error"
      ? "border-signal-red bg-white text-signal-red"
      : "border-iron-100 bg-white text-iron-500";
  return <div className={`rounded-md border px-4 py-3 text-sm ${className}`}>{message}</div>;
}

function belongsTo(document: LibraryDocument) {
  if (document.rfq_package_id) return `RFQ ${document.rfq_package_id.slice(0, 8)}`;
  if (document.project_id) return `Project ${document.project_id.slice(0, 8)}`;
  return "Library";
}

function label(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
