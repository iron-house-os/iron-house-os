import { FormEvent, type ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { KeyRound, ShieldCheck, UserPlus } from "lucide-react";
import { Link } from "react-router-dom";

import {
  DeploymentStatus,
  employeeOnboardingApi,
  EmploymentCategory,
  Invitation,
  OnboardingCreatePayload,
  OnboardingRecord,
  PortalActivation,
  PositionOption,
} from "../api/employeeOnboarding";
import { Employee, fieldOperationsApi } from "../api/fieldOperations";

const today = () => new Date().toISOString().slice(0, 10);

const blankForm = (): OnboardingCreatePayload => ({
  legal_first_name: "",
  legal_last_name: "",
  preferred_name: null,
  personal_email: "",
  mobile_phone: null,
  category: "field_staff",
  position: "green_labourer",
  supervisor_id: null,
  employment_type: "full_time",
  start_date: today(),
  primary_location: null,
  onboarding_package: "standard-field",
});

export function EmployeeOnboardingPage() {
  const [records, setRecords] = useState<OnboardingRecord[]>([]);
  const [positions, setPositions] = useState<PositionOption[]>([]);
  const [supervisors, setSupervisors] = useState<Employee[]>([]);
  const [deployment, setDeployment] = useState<Record<string, DeploymentStatus>>({});
  const [form, setForm] = useState<OnboardingCreatePayload>(blankForm);
  const [correctionNotes, setCorrectionNotes] = useState<Record<string, string>>({});
  const [invitation, setInvitation] = useState<Invitation | null>(null);
  const [credentials, setCredentials] = useState<PortalActivation | null>(null);
  const [actingId, setActingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [onboarding, availablePositions, field] = await Promise.all([
        employeeOnboardingApi.list(),
        employeeOnboardingApi.positions(),
        fieldOperationsApi.bootstrap(),
      ]);
      setRecords(onboarding.items);
      setPositions(availablePositions);
      setSupervisors(field.employees);
      const statusPairs = await Promise.all(
        onboarding.items.map(async (record) => [
          record.id,
          await employeeOnboardingApi.deploymentStatus(record.id),
        ] as const),
      );
      setDeployment(Object.fromEntries(statusPairs));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load employee onboarding.");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const availablePositions = useMemo(
    () => positions.filter((position) => position.category === form.category),
    [form.category, positions],
  );

  function updateForm<Key extends keyof OnboardingCreatePayload>(
    key: Key,
    value: OnboardingCreatePayload[Key],
  ) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function changeCategory(category: EmploymentCategory) {
    const firstPosition = positions.find((position) => position.category === category)?.value ?? "";
    setForm((current) => ({
      ...current,
      category,
      position: firstPosition,
      onboarding_package: category === "field_staff" ? "standard-field" : "standard-office",
    }));
  }

  async function createOnboarding(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setInvitation(null);
    setCredentials(null);
    setActingId("new");
    try {
      await employeeOnboardingApi.create(form);
      setForm(blankForm());
      setMessage("New-hire onboarding record created. Generate the secure invitation when ready.");
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to create onboarding.");
    } finally {
      setActingId(null);
    }
  }

  async function runAction(record: OnboardingRecord, action: () => Promise<unknown>, success: string) {
    setError(null);
    setMessage(null);
    setInvitation(null);
    setCredentials(null);
    setActingId(record.id);
    try {
      await action();
      setMessage(success);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to update onboarding.");
    } finally {
      setActingId(null);
    }
  }

  async function generateInvitation(record: OnboardingRecord) {
    await runAction(
      record,
      async () => {
        const generated = await employeeOnboardingApi.invite(record.id);
        setInvitation(generated);
      },
      "Secure invitation generated. Share it only with the intended employee.",
    );
  }

  async function activate(record: OnboardingRecord) {
    await runAction(
      record,
      async () => {
        const result = await employeeOnboardingApi.activate(record.id);
        setCredentials(result);
      },
      "Employee activated and portal credentials created.",
    );
  }

  return (
    <section className="space-y-6">
      <header className="ihos-brand-surface rounded-xl border border-brand-gold/30 px-6 py-6 text-white shadow-brand">
        <div className="flex items-start gap-4">
          <div className="grid h-12 w-12 place-items-center rounded-xl border border-brand-gold/40 bg-white/10 text-brand-gold">
            <UserPlus />
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-gold">
              Administration and identity
            </div>
            <h1 className="mt-2 text-3xl font-semibold text-brand-silver">Employee onboarding</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-100">
              Create the new-hire record, track employee completion and safety readiness, then issue
              least-privilege portal credentials after approved activation.
            </p>
          </div>
        </div>
      </header>

      {error ? <Notice role="alert" tone="error">{error}</Notice> : null}
      {message ? <Notice role="status" tone="success">{message}</Notice> : null}

      {invitation ? (
        <section className="rounded-xl border border-brand-gold/40 bg-brand-gold/10 p-5 shadow-sm" aria-label="Generated invitation">
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 h-5 w-5 text-brand-gold-dark" />
            <div className="min-w-0">
              <h2 className="font-semibold text-iron-950">Secure invitation generated</h2>
              <p className="mt-1 text-sm text-iron-600">
                This link expires {new Date(invitation.expires_at).toLocaleString("en-CA")}. A resend invalidates the previous link.
              </p>
              <code className="mt-3 block overflow-x-auto rounded-md bg-white px-3 py-2 text-sm text-iron-800">
                {invitation.invite_url}
              </code>
            </div>
          </div>
        </section>
      ) : null}

      {credentials ? (
        <section className="rounded-xl border border-brand-gold/50 bg-white p-5 shadow-sm" aria-label="One-time portal credentials">
          <div className="flex items-start gap-3">
            <KeyRound className="mt-0.5 h-5 w-5 text-brand-gold-dark" />
            <div>
              <h2 className="font-semibold text-iron-950">Copy these credentials now</h2>
              <p className="mt-1 text-sm text-iron-600">
                The temporary password appears only in this response. The employee must replace it at first sign-in.
              </p>
              <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
                <Credential label="Username" value={credentials.username} />
                <Credential label="Temporary password" value={credentials.temporary_password} />
                <Credential label="Portal" value={`${credentials.portal_role} portal`} />
              </dl>
            </div>
          </div>
        </section>
      ) : null}

      <form onSubmit={createOnboarding} className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
        <h2 className="font-semibold text-iron-950">Start a new hire</h2>
        <p className="mt-1 text-sm text-iron-500">Create the pending record before generating an invitation.</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <Field label="Legal first name">
            <input required value={form.legal_first_name} onChange={(event) => updateForm("legal_first_name", event.target.value)} />
          </Field>
          <Field label="Legal last name">
            <input required value={form.legal_last_name} onChange={(event) => updateForm("legal_last_name", event.target.value)} />
          </Field>
          <Field label="Preferred name">
            <input value={form.preferred_name ?? ""} onChange={(event) => updateForm("preferred_name", event.target.value || null)} />
          </Field>
          <Field label="Personal email">
            <input required type="email" value={form.personal_email} onChange={(event) => updateForm("personal_email", event.target.value)} />
          </Field>
          <Field label="Mobile phone">
            <input value={form.mobile_phone ?? ""} onChange={(event) => updateForm("mobile_phone", event.target.value || null)} />
          </Field>
          <Field label="Employment category">
            <select value={form.category} onChange={(event) => changeCategory(event.target.value as EmploymentCategory)}>
              <option value="field_staff">Field staff</option>
              <option value="office_staff">Office staff</option>
            </select>
          </Field>
          <Field label="Position">
            <select required value={form.position} onChange={(event) => updateForm("position", event.target.value)}>
              {availablePositions.map((position) => <option key={position.value} value={position.value}>{position.label}</option>)}
            </select>
          </Field>
          <Field label="Supervisor">
            <select value={form.supervisor_id ?? ""} onChange={(event) => updateForm("supervisor_id", event.target.value || null)}>
              <option value="">Assign later</option>
              {supervisors.map((supervisor) => (
                <option key={supervisor.id} value={supervisor.id}>{supervisor.first_name} {supervisor.last_name}</option>
              ))}
            </select>
          </Field>
          <Field label="Employment type">
            <select value={form.employment_type} onChange={(event) => updateForm("employment_type", event.target.value)}>
              <option value="full_time">Full time</option>
              <option value="part_time">Part time</option>
              <option value="seasonal">Seasonal</option>
              <option value="temporary">Temporary</option>
            </select>
          </Field>
          <Field label="Start date">
            <input required type="date" value={form.start_date} onChange={(event) => updateForm("start_date", event.target.value)} />
          </Field>
          <Field label="Primary location">
            <input value={form.primary_location ?? ""} onChange={(event) => updateForm("primary_location", event.target.value || null)} />
          </Field>
          <Field label="Onboarding package">
            <input value={form.onboarding_package ?? ""} onChange={(event) => updateForm("onboarding_package", event.target.value || null)} />
          </Field>
        </div>
        <button disabled={actingId === "new"} className="mt-5 rounded-md bg-brand-gold px-4 py-2 text-sm font-semibold text-brand-black disabled:opacity-50">
          {actingId === "new" ? "Creating…" : "Create onboarding record"}
        </button>
      </form>

      <section className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-semibold text-iron-950">Onboarding register</h2>
            <p className="mt-1 text-sm text-iron-500">Activation remains blocked until approval and deployment readiness are complete.</p>
          </div>
          <Link to="/worker-orientations" className="rounded-md border border-brand-gold/50 px-3 py-2 text-sm font-semibold text-iron-800">
            Open Worker Orientations
          </Link>
        </div>
        <div className="mt-4 grid gap-4">
          {records.length === 0 ? <p className="text-sm text-iron-500">No onboarding records yet.</p> : null}
          {records.map((record) => {
            const readiness = deployment[record.id];
            const busy = actingId === record.id;
            const canInvite = !["submitted", "approved", "active", "cancelled"].includes(record.status);
            return (
              <article key={record.id} className="rounded-lg border border-iron-100 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="font-semibold text-iron-950">{record.legal_first_name} {record.legal_last_name}</h3>
                    <p className="mt-1 text-sm text-iron-500">{record.personal_email} · {labelValue(record.position)} · starts {record.start_date}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <StatusPill value={labelValue(record.status)} />
                    <ReadinessPill value={readiness?.status ?? "Blocked"} />
                  </div>
                </div>
                <div className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
                  <Fact label="Completion" value={`${record.completion_percent}%`} />
                  <Fact label="Missing items" value={String(record.missing_items.length)} />
                  <Fact label="Required action" value={requiredAction(record, readiness)} />
                </div>
                {readiness?.blockers.length ? <p className="mt-3 text-xs leading-5 text-iron-500">{readiness.blockers.join(" ")}</p> : null}
                {record.correction_note ? <p className="mt-3 rounded-md bg-amber-50 p-3 text-sm text-amber-900">Correction requested: {record.correction_note}</p> : null}
                <div className="mt-4 flex flex-wrap gap-2">
                  {canInvite ? <Action disabled={busy} onClick={() => void generateInvitation(record)}>Generate invitation</Action> : null}
                  {!['active', 'cancelled'].includes(record.status) ? (
                    <Action disabled={busy} onClick={() => void runAction(record, () => employeeOnboardingApi.revoke(record.id), "Invitation revoked and onboarding cancelled.")}>Revoke</Action>
                  ) : null}
                  {record.status === "submitted" ? (
                    <Action disabled={busy} onClick={() => void runAction(record, () => employeeOnboardingApi.approve(record.id), "Onboarding approved. Complete deployment evidence before activation.")}>Approve</Action>
                  ) : null}
                  {record.status === "approved" ? (
                    <Action disabled={busy || readiness?.status !== "Ready"} onClick={() => void activate(record)}>Activate and create login</Action>
                  ) : null}
                </div>
                {record.status === "submitted" ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <input
                      aria-label={`Correction note for ${record.legal_first_name} ${record.legal_last_name}`}
                      placeholder="Correction required"
                      value={correctionNotes[record.id] ?? ""}
                      onChange={(event) => setCorrectionNotes((current) => ({ ...current, [record.id]: event.target.value }))}
                      className="min-w-64 flex-1 rounded-md border border-iron-100 px-3 py-2 text-sm"
                    />
                    <Action
                      disabled={busy || !(correctionNotes[record.id] ?? "").trim()}
                      onClick={() => void runAction(
                        record,
                        () => employeeOnboardingApi.requestCorrections(record.id, correctionNotes[record.id]),
                        "Onboarding returned for corrections.",
                      )}
                    >
                      Request corrections
                    </Action>
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      </section>
    </section>
  );
}

function requiredAction(record: OnboardingRecord, readiness: DeploymentStatus | undefined) {
  if (record.status === "draft") return "Generate invitation";
  if (["invitation_sent", "invitation_opened", "in_progress", "corrections_required"].includes(record.status)) return "Employee completion";
  if (record.status === "submitted") return "Management review";
  if (record.status === "approved" && readiness?.status !== "Ready") return "Orientation evidence";
  if (record.status === "approved") return "Activate employee";
  if (record.status === "active") return "Complete";
  return "No action";
}

function labelValue(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="grid gap-1 text-sm font-medium text-iron-700 [&>input]:rounded-md [&>input]:border [&>input]:px-3 [&>input]:py-2 [&>select]:rounded-md [&>select]:border [&>select]:px-3 [&>select]:py-2">
      {label}
      {children}
    </label>
  );
}

function Notice({ role, tone, children }: { role: "alert" | "status"; tone: "error" | "success"; children: ReactNode }) {
  const style = tone === "error" ? "border-red-200 bg-red-50 text-red-700" : "border-emerald-200 bg-emerald-50 text-emerald-800";
  return <div role={role} className={`rounded-md border p-4 text-sm ${style}`}>{children}</div>;
}

function Credential({ label, value }: { label: string; value: string }) {
  return <div><dt className="text-xs font-semibold uppercase tracking-wide text-iron-500">{label}</dt><dd className="mt-1 break-all font-mono text-iron-950">{value}</dd></div>;
}

function Fact({ label, value }: { label: string; value: string }) {
  return <div><div className="text-xs font-semibold uppercase tracking-wide text-iron-500">{label}</div><div className="mt-1 font-medium text-iron-800">{value}</div></div>;
}

function Action({ children, disabled, onClick }: { children: ReactNode; disabled?: boolean; onClick: () => void }) {
  return <button type="button" disabled={disabled} onClick={onClick} className="rounded-md border border-brand-gold/50 px-3 py-2 text-sm font-semibold text-iron-800 disabled:opacity-40">{children}</button>;
}

function StatusPill({ value }: { value: string }) {
  return <span className="rounded-full bg-iron-100 px-2.5 py-1 text-xs font-semibold text-iron-700">{value}</span>;
}

function ReadinessPill({ value }: { value: DeploymentStatus["status"] }) {
  const tone = value === "Ready" ? "bg-emerald-100 text-emerald-800" : value === "Blocked" ? "bg-red-100 text-red-800" : "bg-amber-100 text-amber-800";
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${tone}`}>{value}</span>;
}
