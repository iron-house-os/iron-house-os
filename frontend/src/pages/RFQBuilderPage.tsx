import {
  CheckCircle2,
  Circle,
  FilePlus2,
  PackageCheck,
  Plus,
  RefreshCw,
  Trash2,
  Users,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import {
  RFQPackage,
  RFQPackageBuildResponse,
  RFQCommunicationWorkflow,
  RFQPackageCreatePayload,
  RFQPackageDocumentCreate,
  RFQPackageDocumentStatus,
  RFQPackageStatus,
  RFQReadiness,
  RFQRecipientStatus,
  RFQWorkflowPreparePayload,
  SupplierResponseCreatePayload,
  SupplierRecipientCreate,
  rfqPackagesApi,
} from "../api/rfqPackages";
import { ProjectScopeNotice } from "../components/ProjectScopeNotice";
import { readEffectiveProjectContext } from "../utils/projectContext";

const recipientStatuses: RFQRecipientStatus[] = ["pending", "sent", "replied", "bounced"];
const documentStatuses: RFQPackageDocumentStatus[] = ["pending", "attached", "not_applicable"];

function blankSupplier(): SupplierRecipientCreate {
  return {
    supplier_id: `manual-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    supplier_name: "",
    category: "",
    recipient_email: "",
    scope_items: [],
  };
}

function defaultDocuments(): RFQPackageDocumentCreate[] {
  return [
    {
      document_type: "drawing",
      title: "Civil drawings",
      required: true,
      storage_uri: "",
      status: "pending",
      metadata: {},
    },
    {
      document_type: "specification",
      title: "Project specifications",
      required: true,
      storage_uri: "",
      status: "pending",
      metadata: {},
    },
    {
      document_type: "addenda",
      title: "Current addenda",
      required: false,
      storage_uri: "",
      status: "pending",
      metadata: {},
    },
  ];
}

export function RFQBuilderPage() {
  const { rfqPackageId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const projectContext = readEffectiveProjectContext(location.search);
  const [packages, setPackages] = useState<RFQPackage[]>([]);
  const [selectedPackage, setSelectedPackage] = useState<RFQPackage | null>(null);
  const [readiness, setReadiness] = useState<RFQReadiness | null>(null);
  const [buildResult, setBuildResult] = useState<RFQPackageBuildResponse | null>(null);
  const [workflow, setWorkflow] = useState<RFQCommunicationWorkflow | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isMutating, setIsMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const list = await rfqPackagesApi.list();
      setPackages(list.items);
      if (rfqPackageId) {
        const [detail, readinessPayload, workflowPayload] = await Promise.all([
          rfqPackagesApi.detail(rfqPackageId),
          rfqPackagesApi.readiness(rfqPackageId),
          rfqPackagesApi.communicationWorkflow(rfqPackageId),
        ]);
        setSelectedPackage(detail);
        setReadiness(readinessPayload);
        setWorkflow(workflowPayload);
      } else {
        setSelectedPackage(null);
        setReadiness(null);
        setWorkflow(null);
      }
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to load RFQs");
    } finally {
      setIsLoading(false);
    }
  }, [rfqPackageId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function createPackage(payload: RFQPackageCreatePayload) {
    setIsMutating(true);
    setError(null);
    try {
      const created = await rfqPackagesApi.create(payload);
      navigate({
        pathname: `/rfq-builder/${created.id}`,
        search: location.search,
      });
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to create RFQ package");
    } finally {
      setIsMutating(false);
    }
  }

  async function mutate(action: () => Promise<RFQPackage>) {
    setIsMutating(true);
    setError(null);
    try {
      const updated = await action();
      setSelectedPackage(updated);
      setBuildResult(null);
      await refresh();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to update RFQ package");
    } finally {
      setIsMutating(false);
    }
  }

  async function buildPackages() {
    if (!selectedPackage) return;
    setIsMutating(true);
    setError(null);
    try {
      setBuildResult(await rfqPackagesApi.build(selectedPackage.id));
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to build RFQ drafts");
    } finally {
      setIsMutating(false);
    }
  }

  async function mutateWorkflow(
    action: () => Promise<RFQCommunicationWorkflow>,
    refreshPackage = false,
  ) {
    setIsMutating(true);
    setError(null);
    try {
      setWorkflow(await action());
      if (refreshPackage) await refresh();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Unable to update communication workflow");
    } finally {
      setIsMutating(false);
    }
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-iron-100 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-iron-950">RFQ Package Builder</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
            Build supplier-specific RFQ scopes, confirm drawing and document attachments, preview draft packages, and manually track delivery responses.
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

      <ProjectScopeNotice name={projectContext.projectName} />
      <div className="rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
        Draft-only workflow: building or changing tracking status does not send email or contact suppliers.
      </div>
      {error ? <StatusNotice tone="error" message={error} /> : null}
      {isLoading ? <StatusNotice tone="neutral" message="Loading RFQ packages..." /> : null}

      <div className="grid gap-6 xl:grid-cols-[380px_1fr]">
        <div className="space-y-6">
          <CreateRFQPackageForm
            defaultProjectName={projectContext.projectName ?? ""}
            isBusy={isMutating}
            onSubmit={(payload) => void createPackage(payload)}
          />
          <RFQPackageList
            packages={packages}
            selectedId={rfqPackageId}
            search={location.search}
          />
        </div>

        {selectedPackage ? (
          <RFQPackageDetail
            key={selectedPackage.id}
            rfqPackage={selectedPackage}
            readiness={readiness}
            buildResult={buildResult}
            workflow={workflow}
            isBusy={isMutating}
            onStatusChange={(status) =>
              void mutate(() => rfqPackagesApi.updateStatus(selectedPackage.id, status))
            }
            onSaveSuppliers={(suppliers) =>
              void mutate(() => rfqPackagesApi.selectSuppliers(selectedPackage.id, suppliers))
            }
            onGenerateScopes={() =>
              void mutate(() => rfqPackagesApi.generateScopes(selectedPackage.id))
            }
            onSaveDocuments={(documents) =>
              void mutate(() => rfqPackagesApi.registerDocuments(selectedPackage.id, documents))
            }
            onRecipientStatus={(recipientId, status, note) =>
              void mutate(() =>
                rfqPackagesApi.updateRecipientStatus(
                  selectedPackage.id,
                  recipientId,
                  status,
                  note,
                ),
              )
            }
            onBuild={() => void buildPackages()}
            onPrepareWorkflow={(payload) =>
              void mutateWorkflow(() =>
                rfqPackagesApi.prepareCommunicationWorkflow(selectedPackage.id, payload),
              )
            }
            onRecordResponse={(payload) =>
              void mutateWorkflow(
                () => rfqPackagesApi.recordSupplierResponse(selectedPackage.id, payload),
                true,
              )
            }
          />
        ) : (
          <div className="rounded-md border border-iron-100 bg-white p-6">
            <h2 className="text-base font-semibold text-iron-950">No RFQ selected</h2>
            <p className="mt-2 text-sm leading-6 text-iron-500">
              Create a package or select one to edit supplier scopes, attachments, and tracking.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

function CreateRFQPackageForm({
  defaultProjectName,
  isBusy,
  onSubmit,
}: {
  defaultProjectName: string;
  isBusy: boolean;
  onSubmit: (payload: RFQPackageCreatePayload) => void;
}) {
  const [title, setTitle] = useState("");
  const [projectName, setProjectName] = useState(defaultProjectName);
  const [scopeSummary, setScopeSummary] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [supplierTargets, setSupplierTargets] = useState("pipe, aggregates, traffic");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim() || !scopeSummary.trim()) return;
    onSubmit({
      title: title.trim(),
      project_name: projectName.trim() || undefined,
      scope_summary: scopeSummary.trim(),
      due_at: dueAt ? new Date(dueAt).toISOString() : undefined,
      supplier_category_targets: supplierTargets
        .split(",")
        .map((target) => target.trim())
        .filter(Boolean),
    });
    setTitle("");
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
            required
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
          />
        </Field>
        <Field label="Package scope">
          <textarea
            required
            value={scopeSummary}
            onChange={(event) => setScopeSummary(event.target.value)}
            className="min-h-24 w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            placeholder="Define the overall supplier pricing scope."
          />
        </Field>
        <Field label="Quote return deadline">
          <input
            type="datetime-local"
            value={dueAt}
            onChange={(event) => setDueAt(event.target.value)}
            className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
          />
        </Field>
        <Field label="Supplier category targets">
          <input
            value={supplierTargets}
            onChange={(event) => setSupplierTargets(event.target.value)}
            className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
          />
        </Field>
      </div>
      <button
        type="submit"
        disabled={isBusy}
        className="mt-5 inline-flex items-center gap-2 rounded-md bg-iron-950 px-3 py-2 text-sm font-semibold text-white disabled:bg-iron-300"
      >
        <Plus className="h-4 w-4" />
        Create package
      </button>
    </form>
  );
}

function RFQPackageList({
  packages,
  selectedId,
  search,
}: {
  packages: RFQPackage[];
  selectedId: string | undefined;
  search: string;
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
              to={{ pathname: `/rfq-builder/${rfqPackage.id}`, search }}
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
  buildResult,
  workflow,
  isBusy,
  onStatusChange,
  onSaveSuppliers,
  onGenerateScopes,
  onSaveDocuments,
  onRecipientStatus,
  onBuild,
  onPrepareWorkflow,
  onRecordResponse,
}: {
  rfqPackage: RFQPackage;
  readiness: RFQReadiness | null;
  buildResult: RFQPackageBuildResponse | null;
  workflow: RFQCommunicationWorkflow | null;
  isBusy: boolean;
  onStatusChange: (status: RFQPackageStatus) => void;
  onSaveSuppliers: (suppliers: SupplierRecipientCreate[]) => void;
  onGenerateScopes: () => void;
  onSaveDocuments: (documents: RFQPackageDocumentCreate[]) => void;
  onRecipientStatus: (recipientId: string, status: RFQRecipientStatus, note: string) => void;
  onBuild: () => void;
  onPrepareWorkflow: (payload: RFQWorkflowPreparePayload) => void;
  onRecordResponse: (payload: SupplierResponseCreatePayload) => void;
}) {
  const statusOptions: RFQPackageStatus[] = ["draft", "assembling", "ready", "issued", "closed"];

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
          <label className="grid gap-1 text-xs font-semibold uppercase tracking-wide text-iron-500">
            Package status
            <select
              value={rfqPackage.status}
              onChange={(event) => onStatusChange(event.target.value as RFQPackageStatus)}
              className="rounded-md border border-iron-100 bg-white px-3 py-2 text-sm font-normal normal-case text-iron-800"
            >
              {statusOptions.map((status) => <option key={status} value={status}>{status}</option>)}
            </select>
          </label>
        </div>
        <dl className="mt-5 grid gap-4 md:grid-cols-3">
          <InfoTile label="Project" value={rfqPackage.project_name ?? "Unassigned"} />
          <InfoTile
            label="Category targets"
            value={rfqPackage.supplier_category_targets.join(", ") || "No targets set"}
          />
          <InfoTile
            label="Quote return"
            value={rfqPackage.due_at ? new Date(rfqPackage.due_at).toLocaleString("en-CA") : "Not set"}
          />
        </dl>
      </div>

      <ReadinessPanel readiness={readiness} />
      <SupplierScopeEditor
        rfqPackage={rfqPackage}
        isBusy={isBusy}
        onSave={onSaveSuppliers}
        onGenerate={onGenerateScopes}
      />
      <DocumentChecklistEditor
        rfqPackage={rfqPackage}
        isBusy={isBusy}
        onSave={onSaveDocuments}
      />
      <RecipientTracking
        rfqPackage={rfqPackage}
        isBusy={isBusy}
        onUpdate={onRecipientStatus}
      />
      <RFQDraftPackages
        result={buildResult}
        isBusy={isBusy}
        onBuild={onBuild}
      />
      <CommunicationWorkflowPanel
        rfqPackage={rfqPackage}
        workflow={workflow}
        isBusy={isBusy}
        onPrepare={onPrepareWorkflow}
        onRecordResponse={onRecordResponse}
      />
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
            All four checks must pass before the draft package is ready for manual issue.
          </p>
        </div>
        <div className="rounded-md bg-iron-950 px-3 py-2 text-sm font-semibold text-white">
          {readiness?.score ?? 0}%
        </div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
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

function SupplierScopeEditor({
  rfqPackage,
  isBusy,
  onSave,
  onGenerate,
}: {
  rfqPackage: RFQPackage;
  isBusy: boolean;
  onSave: (suppliers: SupplierRecipientCreate[]) => void;
  onGenerate: () => void;
}) {
  const [suppliers, setSuppliers] = useState<SupplierRecipientCreate[]>(() =>
    rfqPackage.recipients.length
      ? rfqPackage.recipients.map(({ supplier_id, supplier_name, category, recipient_email, scope_items }) => ({
          supplier_id,
          supplier_name,
          category,
          recipient_email,
          scope_items,
        }))
      : [blankSupplier()],
  );

  useEffect(() => {
    if (!rfqPackage.recipients.length) return;
    setSuppliers(
      rfqPackage.recipients.map(({ supplier_id, supplier_name, category, recipient_email, scope_items }) => ({
        supplier_id,
        supplier_name,
        category,
        recipient_email,
        scope_items,
      })),
    );
  }, [rfqPackage.recipients]);

  function update(index: number, patch: Partial<SupplierRecipientCreate>) {
    setSuppliers((current) =>
      current.map((supplier, supplierIndex) =>
        supplierIndex === index ? { ...supplier, ...patch } : supplier,
      ),
    );
  }

  function save() {
    onSave(
      suppliers
        .filter((supplier) => supplier.supplier_name.trim())
        .map((supplier) => ({
          ...supplier,
          supplier_name: supplier.supplier_name.trim(),
          category: supplier.category?.trim() || null,
          recipient_email: supplier.recipient_email?.trim() || null,
          scope_items: supplier.scope_items.map((item) => item.trim()).filter(Boolean),
        })),
    );
  }

  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4" />
          <div>
            <h2 className="text-base font-semibold text-iron-950">Supplier-specific scopes</h2>
            <p className="text-sm text-iron-500">Leave scope blank to generate civil defaults from the supplier category.</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" disabled={isBusy || !rfqPackage.recipients.length} onClick={onGenerate} className="rounded-md border border-iron-100 px-3 py-2 text-xs font-semibold disabled:text-iron-300">
            Generate missing scopes
          </button>
          <button type="button" onClick={() => setSuppliers((current) => [...current, blankSupplier()])} className="inline-flex items-center gap-1 rounded-md border border-iron-100 px-3 py-2 text-xs font-semibold">
            <Plus className="h-3 w-3" /> Add supplier
          </button>
        </div>
      </div>

      <div className="mt-4 space-y-4">
        {suppliers.map((supplier, index) => (
          <div key={supplier.supplier_id} className="rounded-md border border-iron-100 p-4">
            <div className="grid gap-3 md:grid-cols-[1fr_220px_260px_100px]">
              <input
                aria-label={`Supplier ${index + 1} name`}
                value={supplier.supplier_name}
                onChange={(event) => update(index, { supplier_name: event.target.value })}
                className="rounded-md border border-iron-100 px-3 py-2 text-sm"
                placeholder="Supplier name"
              />
              <input
                aria-label={`Supplier ${index + 1} category`}
                value={supplier.category ?? ""}
                onChange={(event) => update(index, { category: event.target.value })}
                className="rounded-md border border-iron-100 px-3 py-2 text-sm"
                placeholder="pipe, aggregates, traffic..."
              />
              <input
                aria-label={`Supplier ${index + 1} email`}
                type="email"
                value={supplier.recipient_email ?? ""}
                onChange={(event) => update(index, { recipient_email: event.target.value })}
                className="rounded-md border border-iron-100 px-3 py-2 text-sm"
                placeholder="estimating@supplier.example"
              />
              <button
                type="button"
                disabled={suppliers.length <= 1}
                onClick={() => setSuppliers((current) => current.filter((_, rowIndex) => rowIndex !== index))}
                className="inline-flex items-center justify-center gap-1 text-sm text-red-700 disabled:text-iron-300"
              >
                <Trash2 className="h-4 w-4" /> Remove
              </button>
            </div>
            <textarea
              aria-label={`Supplier ${index + 1} scope items`}
              value={supplier.scope_items.join("\n")}
              onChange={(event) => update(index, { scope_items: event.target.value.split("\n") })}
              className="mt-3 min-h-28 w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
              placeholder="One supplier-specific scope item per line"
            />
          </div>
        ))}
      </div>
      <button type="button" disabled={isBusy} onClick={save} className="mt-4 rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white disabled:bg-iron-300">
        Save suppliers and scopes
      </button>
    </div>
  );
}

function DocumentChecklistEditor({
  rfqPackage,
  isBusy,
  onSave,
}: {
  rfqPackage: RFQPackage;
  isBusy: boolean;
  onSave: (documents: RFQPackageDocumentCreate[]) => void;
}) {
  const [documents, setDocuments] = useState<RFQPackageDocumentCreate[]>(() =>
    rfqPackage.documents.length
      ? rfqPackage.documents.map(({ document_type, title, required, storage_uri, status, metadata }) => ({
          document_type,
          title,
          required,
          storage_uri,
          status,
          metadata,
        }))
      : defaultDocuments(),
  );

  useEffect(() => {
    if (!rfqPackage.documents.length) return;
    setDocuments(
      rfqPackage.documents.map(({ document_type, title, required, storage_uri, status, metadata }) => ({
        document_type,
        title,
        required,
        storage_uri,
        status,
        metadata,
      })),
    );
  }, [rfqPackage.documents]);

  function update(index: number, patch: Partial<RFQPackageDocumentCreate>) {
    setDocuments((current) =>
      current.map((document, documentIndex) =>
        documentIndex === index ? { ...document, ...patch } : document,
      ),
    );
  }

  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-iron-950">Drawing and document checklist</h2>
          <p className="mt-1 text-sm text-iron-500">Attached items require a Drive, document, or storage reference.</p>
        </div>
        <button
          type="button"
          onClick={() =>
            setDocuments((current) => [
              ...current,
              {
                document_type: "other",
                title: "",
                required: false,
                storage_uri: "",
                status: "pending",
                metadata: {},
              },
            ])
          }
          className="inline-flex items-center gap-1 rounded-md border border-iron-100 px-3 py-2 text-xs font-semibold"
        >
          <Plus className="h-3 w-3" /> Add document
        </button>
      </div>

      <div className="mt-4 space-y-3">
        {documents.map((document, index) => (
          <div key={index} className="grid gap-3 rounded-md border border-iron-100 p-3 md:grid-cols-[1fr_150px_140px_1fr_90px]">
            <input
              aria-label={`Document ${index + 1} title`}
              value={document.title}
              onChange={(event) => update(index, { title: event.target.value })}
              className="rounded-md border border-iron-100 px-3 py-2 text-sm"
              placeholder="Document title"
            />
            <input
              aria-label={`Document ${index + 1} type`}
              value={document.document_type}
              onChange={(event) => update(index, { document_type: event.target.value })}
              className="rounded-md border border-iron-100 px-3 py-2 text-sm"
              placeholder="drawing"
            />
            <select
              aria-label={`Document ${index + 1} status`}
              value={document.status}
              onChange={(event) => update(index, { status: event.target.value as RFQPackageDocumentStatus })}
              className="rounded-md border border-iron-100 px-3 py-2 text-sm"
            >
              {documentStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
            </select>
            <input
              aria-label={`Document ${index + 1} attachment reference`}
              required={document.status === "attached"}
              value={document.storage_uri ?? ""}
              onChange={(event) => update(index, { storage_uri: event.target.value })}
              className="rounded-md border border-iron-100 px-3 py-2 text-sm"
              placeholder="Drive URL or document reference"
            />
            <label className="flex items-center gap-2 text-sm text-iron-700">
              <input
                aria-label={`Document ${index + 1} required`}
                type="checkbox"
                checked={document.required}
                onChange={(event) => update(index, { required: event.target.checked })}
              />
              Required
            </label>
            <button
              type="button"
              disabled={documents.length <= 1}
              onClick={() => setDocuments((current) => current.filter((_, rowIndex) => rowIndex !== index))}
              className="inline-flex items-center gap-1 text-xs text-red-700 md:col-span-5"
            >
              <Trash2 className="h-3 w-3" /> Remove document
            </button>
          </div>
        ))}
      </div>
      <button
        type="button"
        disabled={isBusy}
        onClick={() => onSave(documents.filter((document) => document.title.trim()))}
        className="mt-4 rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white disabled:bg-iron-300"
      >
        Save attachment checklist
      </button>
    </div>
  );
}

function RecipientTracking({
  rfqPackage,
  isBusy,
  onUpdate,
}: {
  rfqPackage: RFQPackage;
  isBusy: boolean;
  onUpdate: (recipientId: string, status: RFQRecipientStatus, note: string) => void;
}) {
  const [statuses, setStatuses] = useState<Record<string, RFQRecipientStatus>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});

  useEffect(() => {
    setStatuses(Object.fromEntries(rfqPackage.recipients.map((item) => [item.id, item.status])));
    setNotes(Object.fromEntries(rfqPackage.recipients.map((item) => [item.id, item.status_note ?? ""])));
  }, [rfqPackage.id, rfqPackage.recipients]);

  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <h2 className="text-base font-semibold text-iron-950">Supplier delivery tracking</h2>
      <p className="mt-1 text-sm text-iron-500">Manual status log only; no supplier message is sent from this screen.</p>
      <div className="mt-4 space-y-3">
        {rfqPackage.recipients.length ? rfqPackage.recipients.map((recipient) => (
          <div key={recipient.id} className="grid gap-3 rounded-md border border-iron-100 p-3 md:grid-cols-[1fr_150px_1fr_110px]">
            <div>
              <div className="text-sm font-semibold text-iron-950">{recipient.supplier_name}</div>
              <div className="text-xs text-iron-500">{recipient.category ?? "Uncategorized"}</div>
            </div>
            <select
              aria-label={`${recipient.supplier_name} tracking status`}
              value={statuses[recipient.id] ?? recipient.status}
              onChange={(event) =>
                setStatuses((current) => ({
                  ...current,
                  [recipient.id]: event.target.value as RFQRecipientStatus,
                }))
              }
              className="rounded-md border border-iron-100 px-3 py-2 text-sm"
            >
              {recipientStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
            </select>
            <input
              aria-label={`${recipient.supplier_name} tracking note`}
              value={notes[recipient.id] ?? ""}
              onChange={(event) =>
                setNotes((current) => ({ ...current, [recipient.id]: event.target.value }))
              }
              className="rounded-md border border-iron-100 px-3 py-2 text-sm"
              placeholder="Manual tracking note"
            />
            <button
              type="button"
              disabled={isBusy}
              onClick={() =>
                onUpdate(
                  recipient.id,
                  statuses[recipient.id] ?? recipient.status,
                  notes[recipient.id] ?? "",
                )
              }
              className="rounded-md border border-iron-100 px-3 py-2 text-xs font-semibold disabled:text-iron-300"
            >
              Save status
            </button>
          </div>
        )) : <p className="text-sm text-iron-500">Save supplier recipients to begin tracking.</p>}
      </div>
    </div>
  );
}

function RFQDraftPackages({
  result,
  isBusy,
  onBuild,
}: {
  result: RFQPackageBuildResponse | null;
  isBusy: boolean;
  onBuild: () => void;
}) {
  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-base font-semibold text-iron-950">Supplier draft packages</h2>
          <p className="mt-1 text-sm text-iron-500">Generate individualized subjects, scope bodies, and attachment lists for review.</p>
        </div>
        <button
          type="button"
          disabled={isBusy}
          onClick={onBuild}
          className="inline-flex items-center gap-2 rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white disabled:bg-iron-300"
        >
          <PackageCheck className="h-4 w-4" /> Build draft packages
        </button>
      </div>

      {result ? (
        <div className="mt-4 space-y-4">
          {result.ready ? (
            <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
              Package is ready for manual review and issue.
            </div>
          ) : (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              <div className="font-semibold">Drafts generated with readiness blockers</div>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {result.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}
              </ul>
            </div>
          )}
          {result.packages.map((draft) => (
            <details key={draft.recipient_id} className="rounded-md border border-iron-100 p-4">
              <summary className="cursor-pointer text-sm font-semibold text-iron-950">
                {draft.supplier_name} — {draft.subject}
              </summary>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <InfoTile label="Tracking status" value={draft.status} />
                <InfoTile label="Attachments" value={draft.attachment_names.join(", ") || "None"} />
              </div>
              <pre className="mt-3 whitespace-pre-wrap rounded-md bg-iron-50 p-4 text-xs leading-5 text-iron-800">
                {draft.body}
              </pre>
            </details>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function CommunicationWorkflowPanel({
  rfqPackage,
  workflow,
  isBusy,
  onPrepare,
  onRecordResponse,
}: {
  rfqPackage: RFQPackage;
  workflow: RFQCommunicationWorkflow | null;
  isBusy: boolean;
  onPrepare: (payload: RFQWorkflowPreparePayload) => void;
  onRecordResponse: (payload: SupplierResponseCreatePayload) => void;
}) {
  const [driveFolderUri, setDriveFolderUri] = useState(
    workflow?.drive_package?.folder_uri ?? "",
  );
  const [driveManifestUri, setDriveManifestUri] = useState(
    workflow?.drive_package?.manifest_uri ?? "",
  );
  const [senderName, setSenderName] = useState("Iron House");
  const [senderEmail, setSenderEmail] = useState("");
  const [senderPhone, setSenderPhone] = useState("");
  const [supplierId, setSupplierId] = useState(
    rfqPackage.recipients[0]?.supplier_id ?? "",
  );
  const [gmailThreadUri, setGmailThreadUri] = useState("");
  const [driveFileUri, setDriveFileUri] = useState("");
  const [responseNotes, setResponseNotes] = useState("");

  useEffect(() => {
    if (workflow?.drive_package) {
      setDriveFolderUri(workflow.drive_package.folder_uri);
      setDriveManifestUri(workflow.drive_package.manifest_uri ?? "");
    }
  }, [workflow?.drive_package]);

  useEffect(() => {
    if (!rfqPackage.recipients.some((recipient) => recipient.supplier_id === supplierId)) {
      setSupplierId(rfqPackage.recipients[0]?.supplier_id ?? "");
    }
  }, [rfqPackage.recipients, supplierId]);

  function prepare(event: FormEvent) {
    event.preventDefault();
    onPrepare({
      drive_folder_uri: driveFolderUri.trim(),
      drive_manifest_uri: driveManifestUri.trim() || undefined,
      sender_name: senderName.trim() || "Iron House",
      sender_email: senderEmail.trim() || undefined,
      sender_phone: senderPhone.trim() || undefined,
    });
  }

  function recordResponse(event: FormEvent) {
    event.preventDefault();
    if (!supplierId) return;
    onRecordResponse({
      supplier_id: supplierId,
      gmail_thread_uri: gmailThreadUri.trim() || undefined,
      drive_file_uri: driveFileUri.trim() || undefined,
      notes: responseNotes.trim() || undefined,
    });
    setGmailThreadUri("");
    setDriveFileUri("");
    setResponseNotes("");
  }

  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div>
        <h2 className="text-base font-semibold text-iron-950">Gmail + Drive workflow plan</h2>
        <p className="mt-1 text-sm leading-6 text-iron-500">
          Save a reusable Drive manifest and review Gmail-ready drafts. This screen records references only and performs no Google action.
        </p>
      </div>

      <div className="mt-4 rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
        Preview-only: no Gmail draft, email send, Drive folder, or Drive file is created here. Sending always requires separate approval.
      </div>

      <form onSubmit={prepare} className="mt-4 space-y-4">
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Drive package folder reference">
            <input
              aria-label="Drive package folder reference"
              required
              value={driveFolderUri}
              onChange={(event) => setDriveFolderUri(event.target.value)}
              className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
              placeholder="drive://projects/project-id/rfqs/package-id"
            />
          </Field>
          <Field label="Drive manifest reference">
            <input
              aria-label="Drive manifest reference"
              value={driveManifestUri}
              onChange={(event) => setDriveManifestUri(event.target.value)}
              className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
              placeholder="Optional manifest URL or document ID"
            />
          </Field>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <Field label="Sender name">
            <input aria-label="Workflow sender name" value={senderName} onChange={(event) => setSenderName(event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" />
          </Field>
          <Field label="Sender email">
            <input aria-label="Workflow sender email" type="email" value={senderEmail} onChange={(event) => setSenderEmail(event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" />
          </Field>
          <Field label="Sender phone">
            <input aria-label="Workflow sender phone" value={senderPhone} onChange={(event) => setSenderPhone(event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" />
          </Field>
        </div>
        <button type="submit" disabled={isBusy} className="rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white disabled:bg-iron-300">
          Save reusable draft workflow
        </button>
      </form>

      {workflow?.prepared_at ? (
        <div className="mt-5 space-y-3">
          <div className={`rounded-md border p-3 text-sm ${workflow.stale ? "border-amber-200 bg-amber-50 text-amber-900" : "border-emerald-200 bg-emerald-50 text-emerald-800"}`}>
            {workflow.stale
              ? "Saved workflow is stale because RFQ recipients, scopes, or attachments changed. Rebuild it before creating drafts."
              : "Preview-only workflow saved. No Gmail or Drive action was performed."}
          </div>
          {workflow.blockers.length ? (
            <ul className="list-disc space-y-1 pl-5 text-sm text-amber-900">
              {workflow.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}
            </ul>
          ) : null}
          <div className="grid gap-3 md:grid-cols-2">
            {workflow.gmail_drafts.map((draft) => (
              <div key={draft.recipient_id} className="rounded-md border border-iron-100 p-3">
                <div className="text-sm font-semibold text-iron-950">{draft.supplier_name}</div>
                <div className="mt-1 text-xs text-iron-500">To: {draft.to ?? "Recipient email missing"}</div>
                <div className="mt-2 text-xs font-medium text-iron-800">{draft.subject}</div>
                <div className="mt-2 text-xs text-iron-500">
                  {draft.ready_for_draft_creation ? "Ready for separately approved draft creation" : "Blocked"}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="mt-6 border-t border-iron-100 pt-5">
        <h3 className="text-sm font-semibold text-iron-950">Record supplier response</h3>
        <p className="mt-1 text-xs leading-5 text-iron-500">
          Register an existing Gmail thread or Drive file and mark the supplier replied. This does not read or move either item.
        </p>
        <form onSubmit={recordResponse} className="mt-3 grid gap-3 md:grid-cols-2">
          <Field label="Supplier">
            <select aria-label="Response supplier" required value={supplierId} onChange={(event) => setSupplierId(event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm">
              <option value="">Select supplier</option>
              {rfqPackage.recipients.map((recipient) => (
                <option key={recipient.supplier_id} value={recipient.supplier_id}>{recipient.supplier_name}</option>
              ))}
            </select>
          </Field>
          <Field label="Gmail thread reference">
            <input aria-label="Gmail thread reference" value={gmailThreadUri} onChange={(event) => setGmailThreadUri(event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" placeholder="gmail://threads/..." />
          </Field>
          <Field label="Drive response file reference">
            <input aria-label="Drive response file reference" value={driveFileUri} onChange={(event) => setDriveFileUri(event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" placeholder="drive://projects/.../response.pdf" />
          </Field>
          <Field label="Response notes">
            <input aria-label="Response notes" value={responseNotes} onChange={(event) => setResponseNotes(event.target.value)} className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm" placeholder="Quote received and saved" />
          </Field>
          <button type="submit" disabled={isBusy || !supplierId || (!gmailThreadUri.trim() && !driveFileUri.trim())} className="rounded-md border border-iron-100 px-4 py-2 text-sm font-semibold disabled:text-iron-300 md:col-span-2 md:justify-self-start">
            Record response reference
          </button>
        </form>

        {workflow?.supplier_responses.length ? (
          <div className="mt-4 space-y-2">
            {workflow.supplier_responses.map((response) => (
              <div key={response.id} className="rounded-md border border-iron-100 p-3 text-sm">
                <span className="font-semibold text-iron-950">{response.supplier_name}</span>
                <span className="ml-2 text-iron-500">{response.notes ?? "Response recorded"}</span>
              </div>
            ))}
          </div>
        ) : null}
      </div>
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
