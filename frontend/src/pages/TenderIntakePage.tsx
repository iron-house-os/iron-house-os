import { ClipboardList, ExternalLink, FilePlus2, RefreshCw } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { documentsApi, LibraryDocument } from "../api/documents";
import { Project, projectsApi } from "../api/projects";
import { RFQPackage, rfqPackagesApi } from "../api/rfqPackages";
import {
  Tender,
  TenderDocumentIntake,
  TenderIntakePayload,
  tenderStatuses,
  tendersApi,
} from "../api/tenders";

const documentCategories = [
  "drawing",
  "specification",
  "addendum",
  "geotechnical",
  "permit",
  "traffic_control",
  "environmental",
  "quote_request",
  "other",
];

export function TenderIntakePage() {
  const { tenderId } = useParams();
  const navigate = useNavigate();
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [selectedTender, setSelectedTender] = useState<Tender | null>(null);
  const [linkedProject, setLinkedProject] = useState<Project | null>(null);
  const [linkedRfq, setLinkedRfq] = useState<RFQPackage | null>(null);
  const [linkedDocuments, setLinkedDocuments] = useState<LibraryDocument[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const list = await tendersApi.list(statusFilter);
      setTenders(list.items);
      if (tenderId) {
        const tender = await tendersApi.detail(tenderId);
        setSelectedTender(tender);
        const [project, rfq, documents] = await Promise.all([
          tender.project_id ? projectsApi.detail(tender.project_id) : Promise.resolve(null),
          tender.rfq_package_id ? rfqPackagesApi.detail(tender.rfq_package_id) : Promise.resolve(null),
          documentsApi.list({ tender_id: tender.id }),
        ]);
        setLinkedProject(project);
        setLinkedRfq(rfq);
        setLinkedDocuments(documents.items);
      } else {
        setSelectedTender(null);
        setLinkedProject(null);
        setLinkedRfq(null);
        setLinkedDocuments([]);
      }
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to load tenders");
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, tenderId]);

  useEffect(() => {
    // This effect keeps the intake workspace aligned with route and filter changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, [refresh]);

  async function intakeTender(payload: TenderIntakePayload) {
    const result = await tendersApi.intake(payload);
    navigate(`/tenders/${result.tender.id}`);
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-iron-100 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-iron-950">Tender Intake</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
            Manually register tender opportunities and turn them into project workspaces,
            RFQ packages, and document records.
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
      {isLoading ? <Notice tone="neutral" message="Loading tenders..." /> : null}

      <div className="grid gap-6 xl:grid-cols-[440px_1fr]">
        <div className="space-y-6">
          <TenderFilters status={statusFilter} onStatusChange={setStatusFilter} />
          <TenderIntakeForm onSubmit={(payload) => void intakeTender(payload)} />
          <TenderList tenders={tenders} selectedId={tenderId} />
        </div>
        {selectedTender ? (
          <TenderDetail
            tender={selectedTender}
            project={linkedProject}
            rfqPackage={linkedRfq}
            documents={linkedDocuments}
          />
        ) : (
          <div className="rounded-md border border-iron-100 bg-white p-6">
            <h2 className="text-base font-semibold text-iron-950">No tender selected</h2>
            <p className="mt-2 text-sm leading-6 text-iron-500">
              Create or select a tender to review linked workspace records.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

function TenderFilters({
  status,
  onStatusChange,
}: {
  status: string;
  onStatusChange: (value: string) => void;
}) {
  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <h2 className="text-base font-semibold text-iron-950">Tender Filters</h2>
      <select
        value={status}
        onChange={(event) => onStatusChange(event.target.value)}
        className="mt-4 w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
      >
        <option value="">All statuses</option>
        {tenderStatuses.map((item) => (
          <option key={item} value={item}>
            {label(item)}
          </option>
        ))}
      </select>
    </div>
  );
}

function TenderIntakeForm({ onSubmit }: { onSubmit: (payload: TenderIntakePayload) => void }) {
  const [title, setTitle] = useState("");
  const [tenderNumber, setTenderNumber] = useState("");
  const [owner, setOwner] = useState("");
  const [municipality, setMunicipality] = useState("");
  const [closingDate, setClosingDate] = useState("");
  const [questionDeadline, setQuestionDeadline] = useState("");
  const [projectAddress, setProjectAddress] = useState("");
  const [description, setDescription] = useState("");
  const [documentTitle, setDocumentTitle] = useState("");
  const [documentCategory, setDocumentCategory] = useState("drawing");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim()) return;
    const documents: TenderDocumentIntake[] = documentTitle.trim()
      ? [{ title: documentTitle.trim(), category: documentCategory }]
      : [];
    onSubmit({
      title: title.trim(),
      tender_number: tenderNumber.trim() || undefined,
      source: "manual",
      owner: owner.trim() || undefined,
      municipality: municipality.trim() || undefined,
      closing_date: closingDate || undefined,
      question_deadline: questionDeadline || undefined,
      project_address: projectAddress.trim() || undefined,
      description: description.trim() || undefined,
      documents,
    });
    setTitle("");
    setTenderNumber("");
    setOwner("");
    setMunicipality("");
    setClosingDate("");
    setQuestionDeadline("");
    setProjectAddress("");
    setDescription("");
    setDocumentTitle("");
  }

  return (
    <form className="rounded-md border border-iron-100 bg-white p-5" onSubmit={handleSubmit}>
      <div className="mb-4 flex items-center gap-2">
        <FilePlus2 className="h-5 w-5 text-signal-blue" />
        <h2 className="text-base font-semibold text-iron-950">Manual Intake</h2>
      </div>
      <div className="space-y-3">
        <Field label="Tender title">
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            placeholder="Newton Watermain Replacement"
          />
        </Field>
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Tender number">
            <input
              value={tenderNumber}
              onChange={(event) => setTenderNumber(event.target.value)}
              className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            />
          </Field>
          <Field label="Owner">
            <input
              value={owner}
              onChange={(event) => setOwner(event.target.value)}
              className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            />
          </Field>
          <Field label="Municipality">
            <input
              value={municipality}
              onChange={(event) => setMunicipality(event.target.value)}
              className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            />
          </Field>
          <Field label="Closing date">
            <input
              type="date"
              value={closingDate}
              onChange={(event) => setClosingDate(event.target.value)}
              className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            />
          </Field>
          <Field label="Question deadline">
            <input
              type="date"
              value={questionDeadline}
              onChange={(event) => setQuestionDeadline(event.target.value)}
              className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            />
          </Field>
          <Field label="Project address">
            <input
              value={projectAddress}
              onChange={(event) => setProjectAddress(event.target.value)}
              className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            />
          </Field>
        </div>
        <Field label="Description">
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            className="min-h-24 w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            placeholder="Watermain, storm sewer, paving, traffic control..."
          />
        </Field>
        <div className="rounded-md border border-iron-100 bg-iron-50 p-4">
          <h3 className="text-sm font-semibold text-iron-950">Initial tender document</h3>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <input
              value={documentTitle}
              onChange={(event) => setDocumentTitle(event.target.value)}
              className="rounded-md border border-iron-100 px-3 py-2 text-sm"
              placeholder="C-101 Utility Plan"
            />
            <select
              value={documentCategory}
              onChange={(event) => setDocumentCategory(event.target.value)}
              className="rounded-md border border-iron-100 px-3 py-2 text-sm"
            >
              {documentCategories.map((item) => (
                <option key={item} value={item}>
                  {label(item)}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
      <button
        type="submit"
        className="mt-5 inline-flex items-center gap-2 rounded-md bg-iron-950 px-3 py-2 text-sm font-semibold text-white"
      >
        <ClipboardList className="h-4 w-4" />
        Create Intake
      </button>
    </form>
  );
}

function TenderList({
  tenders,
  selectedId,
}: {
  tenders: Tender[];
  selectedId: string | undefined;
}) {
  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <h2 className="text-base font-semibold text-iron-950">Tenders</h2>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-iron-100 text-xs uppercase tracking-wide text-iron-500">
              <th className="py-2 pr-4">Title</th>
              <th className="py-2 pr-4">Municipality</th>
              <th className="py-2 pr-4">Closing</th>
              <th className="py-2 pr-4">Status</th>
            </tr>
          </thead>
          <tbody>
            {tenders.length === 0 ? (
              <tr>
                <td className="py-3 text-iron-500" colSpan={4}>
                  No tenders registered.
                </td>
              </tr>
            ) : (
              tenders.map((tender) => (
                <tr
                  key={tender.id}
                  className={[
                    "border-b border-iron-100 last:border-b-0",
                    selectedId === tender.id ? "bg-iron-50" : "",
                  ].join(" ")}
                >
                  <td className="py-3 pr-4 font-medium text-iron-950">
                    <Link to={`/tenders/${tender.id}`}>{tender.title}</Link>
                  </td>
                  <td className="py-3 pr-4 text-iron-800">
                    {tender.municipality ?? "Unassigned"}
                  </td>
                  <td className="py-3 pr-4 text-iron-800">
                    {tender.closing_date ?? "Not set"}
                  </td>
                  <td className="py-3 pr-4 text-iron-800">{label(tender.status)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TenderDetail({
  tender,
  project,
  rfqPackage,
  documents,
}: {
  tender: Tender;
  project: Project | null;
  rfqPackage: RFQPackage | null;
  documents: LibraryDocument[];
}) {
  return (
    <div className="space-y-6">
      <div className="rounded-md border border-iron-100 bg-white p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="text-xs uppercase tracking-wide text-iron-500">
              {tender.tender_number ?? "Manual intake"}
            </div>
            <h2 className="mt-1 text-2xl font-semibold text-iron-950">{tender.title}</h2>
            <p className="mt-2 text-sm leading-6 text-iron-500">
              {tender.owner ?? "No owner set"} - {tender.municipality ?? "No municipality"}
            </p>
          </div>
          {project ? (
            <Link
              to={`/projects/${project.id}`}
              className="inline-flex items-center gap-2 rounded-md bg-iron-950 px-3 py-2 text-sm font-semibold text-white"
            >
              <ExternalLink className="h-4 w-4" />
              Open Project Workspace
            </Link>
          ) : null}
        </div>
        <dl className="mt-5 grid gap-4 md:grid-cols-3">
          <InfoTile label="Status" value={label(tender.status)} />
          <InfoTile label="Closing date" value={tender.closing_date ?? "Not set"} />
          <InfoTile label="Question deadline" value={tender.question_deadline ?? "Not set"} />
          <InfoTile label="Project" value={project?.name ?? "Not linked"} />
          <InfoTile label="RFQ package" value={rfqPackage?.title ?? "Not linked"} />
          <InfoTile label="Documents" value={String(documents.length)} />
        </dl>
      </div>
      <LinkedRecords tender={tender} rfqPackage={rfqPackage} documents={documents} />
    </div>
  );
}

function LinkedRecords({
  tender,
  rfqPackage,
  documents,
}: {
  tender: Tender;
  rfqPackage: RFQPackage | null;
  documents: LibraryDocument[];
}) {
  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <div className="rounded-md border border-iron-100 bg-white p-5">
        <h2 className="text-base font-semibold text-iron-950">Suggested Supplier Categories</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {tender.suggested_supplier_categories.length === 0 ? (
            <span className="text-sm text-iron-500">No suggestions yet.</span>
          ) : (
            tender.suggested_supplier_categories.map((category) => (
              <span
                key={category}
                className="rounded-md border border-iron-100 bg-iron-50 px-2 py-1 text-xs font-medium text-iron-800"
              >
                {label(category)}
              </span>
            ))
          )}
        </div>
      </div>
      <div className="rounded-md border border-iron-100 bg-white p-5">
        <h2 className="text-base font-semibold text-iron-950">RFQ Package</h2>
        {rfqPackage ? (
          <div className="mt-3 text-sm text-iron-800">
            <Link className="font-semibold text-iron-950" to={`/rfq-builder/${rfqPackage.id}`}>
              {rfqPackage.title}
            </Link>
            <p className="mt-2 text-iron-500">
              {rfqPackage.supplier_category_targets.length} supplier category targets.
            </p>
          </div>
        ) : (
          <p className="mt-3 text-sm text-iron-500">No RFQ package linked.</p>
        )}
      </div>
      <div className="rounded-md border border-iron-100 bg-white p-5 xl:col-span-2">
        <h2 className="text-base font-semibold text-iron-950">Tender Documents</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-iron-100 text-xs uppercase tracking-wide text-iron-500">
                <th className="py-2 pr-4">Title</th>
                <th className="py-2 pr-4">Category</th>
                <th className="py-2 pr-4">Storage URI</th>
              </tr>
            </thead>
            <tbody>
              {documents.length === 0 ? (
                <tr>
                  <td className="py-3 text-iron-500" colSpan={3}>
                    No tender documents linked.
                  </td>
                </tr>
              ) : (
                documents.map((document) => (
                  <tr key={document.id} className="border-b border-iron-100 last:border-b-0">
                    <td className="py-3 pr-4 font-medium text-iron-950">
                      <Link to={`/documents/${document.id}`}>{document.title}</Link>
                    </td>
                    <td className="py-3 pr-4 text-iron-800">{label(document.category)}</td>
                    <td className="py-3 pr-4 text-iron-800">
                      {document.storage_uri ?? "Not registered"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
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

function label(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
