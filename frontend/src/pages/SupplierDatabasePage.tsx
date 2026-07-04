import { ContactRound, Database, Plus, RefreshCw, Save, Search } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  ContactCreatePayload,
  Supplier,
  SupplierCreatePayload,
  SupplierUpdatePayload,
  suppliersApi,
} from "../api/suppliers";

export function SupplierDatabasePage() {
  const { supplierId } = useParams();
  const navigate = useNavigate();
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [selectedSupplier, setSelectedSupplier] = useState<Supplier | null>(null);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const categories = useMemo(
    () =>
      Array.from(new Set(suppliers.map((supplier) => supplier.category).filter(Boolean))).sort(),
    [suppliers],
  );

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const list = await suppliersApi.list({ search, category });
      setSuppliers(list.items);
      if (supplierId) {
        setSelectedSupplier(await suppliersApi.detail(supplierId));
      } else {
        setSelectedSupplier(null);
      }
    } catch (currentError) {
      setError(
        currentError instanceof Error ? currentError.message : "Unable to load suppliers",
      );
    } finally {
      setIsLoading(false);
    }
  }, [category, search, supplierId]);

  useEffect(() => {
    // This effect keeps the supplier workspace aligned with search and route selection.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, [refresh]);

  async function createSupplier(payload: SupplierCreatePayload) {
    const created = await suppliersApi.create(payload);
    navigate(`/suppliers/${created.id}`);
  }

  async function updateSupplier(payload: SupplierUpdatePayload) {
    if (!selectedSupplier) return;
    await suppliersApi.update(selectedSupplier.id, payload);
    await refresh();
  }

  async function replaceContacts(payload: ContactCreatePayload[]) {
    if (!selectedSupplier) return;
    await suppliersApi.replaceContacts(selectedSupplier.id, payload);
    await refresh();
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-iron-100 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-iron-950">Supplier Database</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
            Manage supplier profiles, categories, service areas, and estimating contacts for RFQ
            targeting.
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

      {error ? <Notice message={error} tone="error" /> : null}
      {isLoading ? <Notice message="Loading suppliers..." tone="neutral" /> : null}

      <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
        <div className="space-y-6">
          <SupplierFilters
            search={search}
            category={category}
            categories={categories}
            onSearchChange={setSearch}
            onCategoryChange={setCategory}
          />
          <CreateSupplierForm onSubmit={(payload) => void createSupplier(payload)} />
          <SupplierList suppliers={suppliers} selectedId={supplierId} />
        </div>

        {selectedSupplier ? (
          <SupplierDetail
            supplier={selectedSupplier}
            onUpdate={(payload) => void updateSupplier(payload)}
            onReplaceContacts={(payload) => void replaceContacts(payload)}
          />
        ) : (
          <div className="rounded-md border border-iron-100 bg-white p-6">
            <h2 className="text-base font-semibold text-iron-950">No supplier selected</h2>
            <p className="mt-2 text-sm leading-6 text-iron-500">
              Create or select a supplier to review profile details and contacts.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

function SupplierFilters({
  search,
  category,
  categories,
  onSearchChange,
  onCategoryChange,
}: {
  search: string;
  category: string;
  categories: (string | null)[];
  onSearchChange: (value: string) => void;
  onCategoryChange: (value: string) => void;
}) {
  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div className="mb-4 flex items-center gap-2">
        <Search className="h-5 w-5 text-signal-blue" />
        <h2 className="text-base font-semibold text-iron-950">Search Suppliers</h2>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <input
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
          placeholder="Name, category, service area"
        />
        <select
          value={category}
          onChange={(event) => onCategoryChange(event.target.value)}
          className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
        >
          <option value="">All categories</option>
          {categories.map((item) => (
            <option key={item ?? ""} value={item ?? ""}>
              {item}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

function CreateSupplierForm({ onSubmit }: { onSubmit: (payload: SupplierCreatePayload) => void }) {
  const [name, setName] = useState("");
  const [category, setCategory] = useState("pipe");
  const [serviceArea, setServiceArea] = useState("Lower Mainland");
  const [contactEmail, setContactEmail] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) return;
    onSubmit({
      name: name.trim(),
      category: category.trim() || undefined,
      service_area: serviceArea.trim() || undefined,
      contacts: contactEmail.trim()
        ? [
            {
              first_name: "Primary",
              last_name: "Contact",
              email: contactEmail.trim(),
              phone: null,
              role: "Estimating",
            },
          ]
        : [],
    });
    setName("");
    setContactEmail("");
  }

  return (
    <form className="rounded-md border border-iron-100 bg-white p-5" onSubmit={handleSubmit}>
      <div className="mb-4 flex items-center gap-2">
        <Plus className="h-5 w-5 text-signal-green" />
        <h2 className="text-base font-semibold text-iron-950">Create Supplier</h2>
      </div>
      <div className="space-y-3">
        <Field label="Supplier name">
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            placeholder="Pacific Pipe Supply"
          />
        </Field>
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Category">
            <input
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            />
          </Field>
          <Field label="Service area">
            <input
              value={serviceArea}
              onChange={(event) => setServiceArea(event.target.value)}
              className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            />
          </Field>
        </div>
        <Field label="Primary contact email">
          <input
            value={contactEmail}
            onChange={(event) => setContactEmail(event.target.value)}
            className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
            placeholder="estimating@example.com"
          />
        </Field>
      </div>
      <button
        type="submit"
        className="mt-5 inline-flex items-center gap-2 rounded-md bg-iron-950 px-3 py-2 text-sm font-semibold text-white"
      >
        <Database className="h-4 w-4" />
        Create
      </button>
    </form>
  );
}

function SupplierList({
  suppliers,
  selectedId,
}: {
  suppliers: Supplier[];
  selectedId: string | undefined;
}) {
  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <h2 className="text-base font-semibold text-iron-950">Suppliers</h2>
      <div className="mt-4 space-y-2">
        {suppliers.length === 0 ? (
          <p className="text-sm text-iron-500">No suppliers found.</p>
        ) : (
          suppliers.map((supplier) => (
            <Link
              key={supplier.id}
              to={`/suppliers/${supplier.id}`}
              className={[
                "block rounded-md border px-3 py-3 text-sm transition",
                selectedId === supplier.id
                  ? "border-iron-950 bg-iron-950 text-white"
                  : "border-iron-100 hover:border-iron-500",
              ].join(" ")}
            >
              <div className="font-semibold">{supplier.name}</div>
              <div className="mt-1 text-xs opacity-75">
                {supplier.category ?? "Uncategorized"} · {supplier.service_area ?? "No area"}
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}

function SupplierDetail({
  supplier,
  onUpdate,
  onReplaceContacts,
}: {
  supplier: Supplier;
  onUpdate: (payload: SupplierUpdatePayload) => void;
  onReplaceContacts: (payload: ContactCreatePayload[]) => void;
}) {
  return (
    <div className="space-y-6">
      <div className="rounded-md border border-iron-100 bg-white p-5">
        <div className="text-xs uppercase tracking-wide text-iron-500">Supplier Profile</div>
        <h2 className="mt-1 text-2xl font-semibold text-iron-950">{supplier.name}</h2>
        <p className="mt-2 text-sm leading-6 text-iron-500">
          {supplier.notes ?? "No supplier notes yet."}
        </p>
        <dl className="mt-5 grid gap-4 md:grid-cols-3">
          <InfoTile label="Category" value={supplier.category ?? "Uncategorized"} />
          <InfoTile label="Service area" value={supplier.service_area ?? "Unassigned"} />
          <InfoTile label="Contacts" value={String(supplier.contacts.length)} />
        </dl>
      </div>
      <EditSupplierForm key={supplier.id} supplier={supplier} onSubmit={onUpdate} />
      <ContactsPanel supplier={supplier} onReplaceContacts={onReplaceContacts} />
    </div>
  );
}

function EditSupplierForm({
  supplier,
  onSubmit,
}: {
  supplier: Supplier;
  onSubmit: (payload: SupplierUpdatePayload) => void;
}) {
  const [category, setCategory] = useState(supplier.category ?? "");
  const [serviceArea, setServiceArea] = useState(supplier.service_area ?? "");
  const [notes, setNotes] = useState(supplier.notes ?? "");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({
      category: category.trim() || undefined,
      service_area: serviceArea.trim() || undefined,
      notes: notes.trim() || undefined,
    });
  }

  return (
    <form className="rounded-md border border-iron-100 bg-white p-5" onSubmit={handleSubmit}>
      <div className="mb-4 flex items-center gap-2">
        <Save className="h-5 w-5 text-signal-blue" />
        <h2 className="text-base font-semibold text-iron-950">Profile Details</h2>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <Field label="Category">
          <input
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
          />
        </Field>
        <Field label="Service area">
          <input
            value={serviceArea}
            onChange={(event) => setServiceArea(event.target.value)}
            className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
          />
        </Field>
      </div>
      <Field label="Notes">
        <textarea
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          className="mt-1 min-h-24 w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
        />
      </Field>
      <button
        type="submit"
        className="mt-5 inline-flex items-center gap-2 rounded-md bg-iron-950 px-3 py-2 text-sm font-semibold text-white"
      >
        <Save className="h-4 w-4" />
        Save
      </button>
    </form>
  );
}

function ContactsPanel({
  supplier,
  onReplaceContacts,
}: {
  supplier: Supplier;
  onReplaceContacts: (payload: ContactCreatePayload[]) => void;
}) {
  const [email, setEmail] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!email.trim()) return;
    onReplaceContacts([
      {
        first_name: "Primary",
        last_name: "Contact",
        email: email.trim(),
        phone: null,
        role: "Estimating",
      },
    ]);
    setEmail("");
  }

  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div className="mb-4 flex items-center gap-2">
        <ContactRound className="h-5 w-5 text-signal-green" />
        <h2 className="text-base font-semibold text-iron-950">Contacts</h2>
      </div>
      <Table
        headers={["Name", "Email", "Phone", "Role"]}
        rows={supplier.contacts.map((contact) => [
          `${contact.first_name} ${contact.last_name ?? ""}`.trim(),
          contact.email ?? "",
          contact.phone ?? "",
          contact.role ?? "",
        ])}
      />
      <form className="mt-4 flex flex-col gap-3 md:flex-row" onSubmit={handleSubmit}>
        <input
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="w-full rounded-md border border-iron-100 px-3 py-2 text-sm"
          placeholder="new-contact@example.com"
        />
        <button
          type="submit"
          className="inline-flex items-center justify-center gap-2 rounded-md border border-iron-100 px-3 py-2 text-sm font-semibold text-iron-800"
        >
          Replace
        </button>
      </form>
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
          {rows.length === 0 ? (
            <tr>
              <td className="py-3 text-iron-500" colSpan={headers.length}>
                No contacts registered.
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr key={row.join("-")} className="border-b border-iron-100 last:border-b-0">
                {row.map((cell) => (
                  <td key={cell} className="py-3 pr-4 text-iron-800">
                    {cell}
                  </td>
                ))}
              </tr>
            ))
          )}
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

function Notice({ tone, message }: { tone: "neutral" | "error"; message: string }) {
  const className =
    tone === "error"
      ? "border-signal-red bg-white text-signal-red"
      : "border-iron-100 bg-white text-iron-500";
  return <div className={`rounded-md border px-4 py-3 text-sm ${className}`}>{message}</div>;
}
