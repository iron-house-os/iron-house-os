import { CheckCircle2, Circle, FilePlus2, Plus, RefreshCw, Send, Users } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  RFQPackage,
  RFQPackageCreatePayload,
  RFQPackageStatus,
  RFQReadiness,
  rfqPackagesApi,
} from "../api/rfqPackages";

const sampleSuppliers = [
  { supplier_id: "supplier-001", supplier_name: "Pacific Pipe Supply", category: "pipe" },
  { supplier_id: "supplier-002", supplier_name: "Fraser Valley Aggregates", category: "aggregates" },
  { supplier_id: "supplier-003", supplier_name: "Coastal Traffic Control", category: "traffic" },
];

const sampleDocuments = [
  {
    document_type: "drawing",
    title: "Civil drawings",
    required: true,
    storage_uri: null,
    metadata: { source: "manual registration" },
  },
  {
    document_type: "specification",
    title: "Project specifications",
    required: true,
    storage_uri: null,
    metadata: { source: "manual registration" },
  },
  {
    document_type: "addenda",
    title: "Addenda log",
    required: false,
    storage_uri: null,
    metadata: { source: "manual registration" },
  },
];

export function RFQBuilderPage() {
  const { rfqPackageId } = useParams();
  const navigate = useNavigate();
  const [packages, setPackages] = useState<RFQPackage[]>([]);
  const [selectedPackage, setSelectedPackage] = useState<RFQPackage | null>(null);
  const [readiness, setReadiness] = useState<RFQReadiness | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const list = await rfqPackagesApi.list();
      setPackages(list.items);
      if (rfqPackageId) {
        const [detail, readinessPayload] = await Promise.all([
          rfqPackagesApi.detail(rfqPackageId),
          rfqPackagesApi.readiness(rfqPackageId),
        ]);
        setSelectedPackage(detail);
        setReadiness(readinessPayload);
      } else {
        setSelectedPackage(null);
        setReadiness(null);
      }
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to load RFQs");
    } finally {
      setIsLoading(false);
    }
  }, [rfqPackageId]);

  useEffect(() => {
    // This effect synchronizes the page with the backend when the selected RFQ changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, [refresh]);

  async function createPackage(payload: RFQPackageCreatePayload) {
    const created = await rfqPackagesApi.create(payload);
    navigate(`/rfq-builder/${created.id}`);
  }

  async function updateStatus(status: RFQPackageStatus) {
    if (!selectedPackage) return;
    await rfqPackagesApi.updateStatus(selectedPackage.id, status);
    await refresh();
  }

  async function selectSuppliers() {
    if (!selectedPackage) return;
    await rfqPackagesApi.selectSuppliers(selectedPackage.id, sampleSuppliers);
    await refresh();
  }

  async function registerDocuments() {
    if (!selectedPackage) return;
    await rfqPackagesApi.registerDocuments(selectedPackage.id, sampleDocuments);
    await refresh();
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-iron-100 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-iron-950">RFQ Package Builder</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
            Create supplier RFQ packages, select recipients, register required bid documents, and
            review package readiness before future issue automation is added.
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

      {error ? <StatusNotice tone="error" message={error} /> : null}
      {isLoading ? <StatusNotice tone="neutral" message="Loading RFQ packages..." /> : null}

      <div className="grid gap-6 xl:grid-cols-[380px_1fr]">
        <div className="space-y-6">
          <CreateRFQPackageForm onSubmit={(payload) => void createPackage(payload)} />
          <RFQPackageList packages={packages} selectedId={rfqPackageId} />
        </div>

        {selectedPackage ? (
          <RFQPackageDetail
            rfqPackage={selectedPackage}
            readiness={readiness}
            onStatusChange={(status) => void updateStatus(status)}
            onSelectSuppliers={() => void selectSuppliers()}
            onRegisterDocuments={() => void registerDocuments()}
          />
        ) : (
          <div className="rounded-md border border-iron-100 bg-white p-6">
            <h2 className="text-base font-semibold text-iron-950">No RFQ selected</h2>
            <p className="mt-2 text-sm leading-6 text-iron-500">
              Create a package or select one from the list to review recipients, documents, and
              readiness.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

function CreateRFQPackageForm({
  onSubmit,
}: {
  onSubmit: (payload: RFQPackageCreatePayload) => void;
}) {
  const [title, setTitle] = useState("");
  const [projectName, setProjectName] = useState("");
  const [scopeSummary, setScopeSummary] = useState("");
  const [supplierTargets, setSupplierTargets] = useState("pipe, aggregates, traffic");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim()) return;
    onSubmit({
      title: title.trim(),
      project_name: projectName.trim() || undefined,
      scope_summary: scopeSummary.trim() || undefined,
      supplier_category_targets: supplierTargets
        .split(",")
        .map((target) => target.trim())
        .filter(Boolean),
    });
    setTitle("");
    setProjectName("");
    setScopeSummary("");
  }

  return (
    <form className="rounded-md border border-iron-100 bg-white p-5" onSubmit={handleSubmit}>
      <div className="mb-4 flex items-center gap-2">
        <FilePlus2 className="h-5 w-5 text-signal-blue" />
        <h2 className="text-base font-semibold text-iron-950">Create RFQ Package</h2>
      </div>
      <div className="space-y-4">
        <Field label="Package title">
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            placeholder="Stormwater pipe supply RFQ"
          />
        </Field>
        <Field label="Project name">
          <input
            value={projectName}
            onChange={(event) => setProjectName(event.target.value)}
            className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            placeholder="King George utility upgrade"
          />
        </Field>
        <Field label="Scope summary">
          <textarea
            value={scopeSummary}
            onChange={(event) => setScopeSummary(event.target.value)}
            className="min-h-24 w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            placeholder="Summarize the quote request scope."
          />
        </Field>
        <Field label="Supplier category targeting">
          <input
            value={supplierTargets}
            onChange={(event) => setSupplierTargets(event.target.value)}
            className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
          />
        </Field>
      </div>
      <button
        type="submit"
        className="mt-5 inline-flex items-center gap-2 rounded-md bg-iron-950 px-3 py-2 text-sm font-semibold text-white"
      >
        <Plus className="h-4 w-4" />
        Create
      </button>
    </form>
  );
}

function RFQPackageList({
  packages,
  selectedId,
}: {
  packages: RFQPackage[];
  selectedId: string | undefined;
}) {
  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <h2 className="text-base font-semibold text-iron-950">RFQ Packages</h2>
      <div className="mt-4 space-y-2">
        {packages.length === 0 ? (
          <p className="text-sm text-iron-500">No RFQ packages yet.</p>
        ) : (
          packages.map((rfqPackage) => (
            <Link
              key={rfqPackage.id}
              to={`/rfq-builder/${rfqPackage.id}`}
              className={[
                "block rounded-md border px-3 py-3 text-sm transition",
                selectedId === rfqPackage.id
                  ? "border-iron-950 bg-iron-950 text-white"
                  : "border-iron-100 hover:border-iron-500",
              ].join(" ")}
            >
              <div className="font-semibold">{rfqPackage.title}</div>
              <div className="mt-1 text-xs opacity-75">{rfqPackage.status}</div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}

function RFQPackageDetail({
  rfqPackage,
  readiness,
  onStatusChange,
  onSelectSuppliers,
  onRegisterDocuments,
}: {
  rfqPackage: RFQPackage;
  readiness: RFQReadiness | null;
  onStatusChange: (status: RFQPackageStatus) => void;
  onSelectSuppliers: () => void;
  onRegisterDocuments: () => void;
}) {
  const statusOptions: RFQPackageStatus[] = ["draft", "assembling", "ready", "issued", "closed"];
  const categoryTargets = useMemo(
    () => rfqPackage.supplier_category_targets.join(", ") || "No targets set",
    [rfqPackage.supplier_category_targets],
  );

  return (
    <div className="space-y-6">
      <div className="rounded-md border border-iron-100 bg-white p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="text-xs uppercase tracking-wide text-iron-500">RFQ Package</div>
            <h2 className="mt-1 text-2xl font-semibold text-iron-950">{rfqPackage.title}</h2>
            <p className="mt-2 text-sm leading-6 text-iron-500">
              {rfqPackage.scope_summary ?? "No scope summary yet."}
            </p>
          </div>
          <select
            value={rfqPackage.status}
            onChange={(event) => onStatusChange(event.target.value as RFQPackageStatus)}
            className="rounded-md border border-iron-100 bg-white px-3 py-2 text-sm"
          >
            {statusOptions.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>
        <dl className="mt-5 grid gap-4 md:grid-cols-3">
          <InfoTile label="Project" value={rfqPackage.project_name ?? "Unassigned"} />
          <InfoTile label="Category targets" value={categoryTargets} />
          <InfoTile label="Status" value={rfqPackage.status} />
        </dl>
      </div>

      <ReadinessPanel readiness={readiness} />
      <SupplierSelectionTable rfqPackage={rfqPackage} onSelectSuppliers={onSelectSuppliers} />
      <DocumentChecklistTable rfqPackage={rfqPackage} onRegisterDocuments={onRegisterDocuments} />
    </div>
  );
}

function ReadinessPanel({ readiness }: { readiness: RFQReadiness | null }) {
  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-iron-950">Package Readiness</h2>
          <p className="mt-1 text-sm text-iron-500">
            Summary payload for deciding whether the package is ready to issue later.
          </p>
        </div>
        <div className="rounded-md bg-iron-950 px-3 py-2 text-sm font-semibold text-white">
          {readiness?.score ?? 0}%
        </div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {readiness?.items.map((item) => (
          <div key={item.key} className="rounded-md border border-iron-100 p-3">
            <div className="flex items-center gap-2 text-sm font-medium text-iron-950">
              {item.ready ? (
                <CheckCircle2 className="h-4 w-4 text-signal-green" />
              ) : (
                <Circle className="h-4 w-4 text-iron-500" />
              )}
              {item.label}
            </div>
            <p className="mt-2 text-xs leading-5 text-iron-500">{item.detail}</p>
          </div>
        )) ?? <p className="text-sm text-iron-500">Readiness not loaded.</p>}
      </div>
    </div>
  );
}

function SupplierSelectionTable({
  rfqPackage,
  onSelectSuppliers,
}: {
  rfqPackage: RFQPackage;
  onSelectSuppliers: () => void;
}) {
  const rows = rfqPackage.recipients.length > 0 ? rfqPackage.recipients : sampleSuppliers;

  return (
    <DataPanel
      icon={<Users className="h-4 w-4" />}
      title="Supplier Selection"
      actionLabel="Use Placeholder Selection"
      onAction={onSelectSuppliers}
    >
      <Table
        headers={["Supplier", "Category", "Status"]}
        rows={rows.map((row) => [
          row.supplier_name,
          row.category ?? "Uncategorized",
          "status" in row ? row.status : "candidate",
        ])}
      />
    </DataPanel>
  );
}

function DocumentChecklistTable({
  rfqPackage,
  onRegisterDocuments,
}: {
  rfqPackage: RFQPackage;
  onRegisterDocuments: () => void;
}) {
  const rows = rfqPackage.documents.length > 0 ? rfqPackage.documents : sampleDocuments;

  return (
    <DataPanel
      icon={<Send className="h-4 w-4" />}
      title="Document Checklist"
      actionLabel="Register Placeholder Documents"
      onAction={onRegisterDocuments}
    >
      <Table
        headers={["Document", "Type", "Required", "Status"]}
        rows={rows.map((row) => [
          row.title,
          row.document_type,
          row.required ? "Required" : "Optional",
          "status" in row ? row.status : "pending",
        ])}
      />
    </DataPanel>
  );
}

function DataPanel({
  icon,
  title,
  actionLabel,
  onAction,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  actionLabel: string;
  onAction: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div className="mb-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-base font-semibold text-iron-950">
          {icon}
          {title}
        </div>
        <button
          type="button"
          onClick={onAction}
          className="rounded-md border border-iron-100 px-3 py-2 text-xs font-semibold text-iron-800"
        >
          {actionLabel}
        </button>
      </div>
      {children}
    </div>
  );
}

function Table({ headers, rows }: { headers: string[]; rows: string[][] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-iron-100 text-xs uppercase tracking-wide text-iron-500">
            {headers.map((header) => (
              <th key={header} className="py-2 pr-4 font-semibold">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.join("-")} className="border-b border-iron-100 last:border-b-0">
              {row.map((cell) => (
                <td key={cell} className="py-3 pr-4 text-iron-800">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function InfoTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-iron-100 bg-iron-50 p-3">
      <dt className="text-xs uppercase tracking-wide text-iron-500">{label}</dt>
      <dd className="mt-1 text-sm font-semibold text-iron-950">{value}</dd>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-iron-800">{label}</span>
      {children}
    </label>
  );
}

function StatusNotice({ tone, message }: { tone: "neutral" | "error"; message: string }) {
  const className =
    tone === "error"
      ? "border-signal-red bg-white text-signal-red"
      : "border-iron-100 bg-white text-iron-500";
  return <div className={`rounded-md border px-4 py-3 text-sm ${className}`}>{message}</div>;
}
