import { FormEvent, type ReactNode, useCallback, useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import {
  DeploymentStatus,
  employeeOnboardingApi,
  OnboardingRecord,
  orientationTopicCodes,
} from "../api/employeeOnboarding";

type OrientationTopicCode = (typeof orientationTopicCodes)[number];
type TopicState = Record<
  OrientationTopicCode,
  {
    applicability: "applicable" | "not_applicable";
    completed: boolean;
    notApplicableBasis: string;
  }
>;

const blankTopics = () =>
  Object.fromEntries(
    orientationTopicCodes.map((code) => [
      code,
      { applicability: "applicable", completed: false, notApplicableBasis: "" },
    ]),
  ) as TopicState;

function topicLabel(code: OrientationTopicCode) {
  return code
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function completedTopicEvidence(code: OrientationTopicCode) {
  return `Completed in the orientation checklist: ${topicLabel(code)}.`;
}

function topicIsRecorded(topic: TopicState[OrientationTopicCode]) {
  return topic.applicability === "applicable"
    ? topic.completed
    : topic.notApplicableBasis.trim().length > 0;
}

export function WorkerOrientationsPage() {
  const [workers, setWorkers] = useState<OnboardingRecord[]>([]);
  const [statuses, setStatuses] = useState<Record<string, DeploymentStatus>>({});
  const [checkingStatusIds, setCheckingStatusIds] = useState<Set<string>>(new Set());
  const [unverifiedStatusIds, setUnverifiedStatusIds] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState("");
  const [scope, setScope] = useState<"company" | "site">("company");
  const [siteName, setSiteName] = useState("");
  const [trigger, setTrigger] = useState("new_hire");
  const [instructor, setInstructor] = useState("");
  const [supervisor, setSupervisor] = useState("");
  const [version, setVersion] = useState("");
  const [competency, setCompetency] = useState("not_assessed");
  const [topics, setTopics] = useState<TopicState>(blankTopics);
  const [ppe, setPpe] = useState(false);
  const [qualifications, setQualifications] = useState(false);
  const [ack, setAck] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const records = (await employeeOnboardingApi.list()).items;
      setWorkers(records);
      setStatuses({});
      setCheckingStatusIds(new Set(records.map((worker) => worker.id)));
      setUnverifiedStatusIds(new Set());
      const results = await Promise.allSettled(
        records.map(async (worker) => {
          try {
            return [worker.id, await employeeOnboardingApi.deploymentStatus(worker.id)] as const;
          } catch {
            return [worker.id, await employeeOnboardingApi.deploymentStatus(worker.id)] as const;
          }
        }),
      );
      const verifiedPairs: Array<readonly [string, DeploymentStatus]> = [];
      const unverifiedIds = new Set<string>();
      results.forEach((result, index) => {
        if (result.status === "fulfilled") {
          verifiedPairs.push(result.value);
        } else {
          unverifiedIds.add(records[index].id);
        }
      });
      setStatuses(Object.fromEntries(verifiedPairs));
      setCheckingStatusIds(new Set());
      setUnverifiedStatusIds(unverifiedIds);
      setSelected((current) => current || records[0]?.id || "");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load orientations.");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const recordedTopicCount = orientationTopicCodes.filter((code) =>
    topicIsRecorded(topics[code]),
  ).length;
  const topicsReady = recordedTopicCount === orientationTopicCodes.length;

  function setTopicCompleted(code: OrientationTopicCode, completed: boolean) {
    setTopics((current) => ({
      ...current,
      [code]: {
        ...current[code],
        applicability: "applicable",
        completed,
        notApplicableBasis: "",
      },
    }));
  }

  function setTopicNotApplicable(code: OrientationTopicCode, notApplicable: boolean) {
    setTopics((current) => ({
      ...current,
      [code]: {
        ...current[code],
        applicability: notApplicable ? "not_applicable" : "applicable",
        completed: false,
        notApplicableBasis: "",
      },
    }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    if (!topicsReady) {
      setError("Complete every orientation topic or record why it is not applicable.");
      return;
    }

    try {
      await employeeOnboardingApi.createOrientation(selected, {
        scope,
        site_name: scope === "site" ? siteName : null,
        trigger,
        orientation_date: new Date().toISOString().slice(0, 10),
        instructor_name: instructor,
        supervisor_name: supervisor,
        document_version: version,
        competency_result: competency,
        ppe_verified: ppe,
        qualifications_verified: qualifications,
        worker_acknowledged: ack,
        worker_acknowledged_at: ack ? new Date().toISOString() : null,
        supporting_document_ids: [],
        notes: null,
        topics: orientationTopicCodes.map((code) => ({
          code,
          applicability: topics[code].applicability,
          evidence:
            topics[code].applicability === "applicable"
              ? completedTopicEvidence(code)
              : null,
          not_applicable_basis:
            topics[code].applicability === "not_applicable"
              ? topics[code].notApplicableBasis.trim()
              : null,
        })),
      });
      setMessage("Immutable orientation record saved.");
      setTopics(blankTopics());
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to save orientation.");
    }
  }

  return (
    <section className="space-y-6">
      <header className="ihos-brand-surface rounded-xl border border-brand-gold/30 px-6 py-6 text-white shadow-brand">
        <div className="flex items-start gap-4">
          <div className="grid h-12 w-12 place-items-center rounded-xl border border-brand-gold/40 bg-white/10 text-brand-gold">
            <ShieldCheck />
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-gold">
              Safety and OHS
            </div>
            <h1 className="mt-2 text-3xl font-semibold text-brand-silver">Worker orientations</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-100">
              Company and workplace-specific evidence, competency, PPE and qualification controls
              before deployment.
            </p>
          </div>
        </div>
      </header>

      {error ? (
        <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <span>{error}</span>
          <button type="button" onClick={() => void refresh()} className="min-h-11 rounded-md border border-red-300 bg-white px-4 font-semibold">
            Retry
          </button>
        </div>
      ) : null}
      {checkingStatusIds.size ? (
        <div
          role="status"
          className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
        >
          Checking deployment status for {checkingStatusIds.size} worker
          {checkingStatusIds.size === 1 ? "" : "s"}. Workers are not cleared until verification
          finishes.
        </div>
      ) : null}
      {unverifiedStatusIds.size ? (
        <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          <span>
            Deployment status could not be verified for {unverifiedStatusIds.size} worker{unverifiedStatusIds.size === 1 ? "" : "s"}. Treat affected workers as blocked until verification succeeds.
          </span>
          <button type="button" onClick={() => void refresh()} className="min-h-11 rounded-md border border-amber-400 bg-white px-4 font-semibold">
            Retry status
          </button>
        </div>
      ) : null}
      {message ? (
        <div role="status" className="rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
          {message}
        </div>
      ) : null}

      <section className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
        <h2 className="font-semibold text-iron-950">Deployment board</h2>
        <div className="mt-4 grid gap-3">
          {workers.map((worker) => {
            const status = statuses[worker.id];
            const checking = checkingStatusIds.has(worker.id);
            return (
              <button
                type="button"
                onClick={() => setSelected(worker.id)}
                key={worker.id}
                className={`rounded-md border p-4 text-left ${selected === worker.id ? "border-brand-gold" : "border-iron-100"}`}
              >
                <div className="flex flex-wrap justify-between gap-2">
                  <strong>
                    {worker.legal_first_name} {worker.legal_last_name}
                  </strong>
                  <Status value={status?.status ?? (checking ? "Checking status" : "Status unavailable")} />
                </div>
                <div className="mt-1 text-sm text-iron-500">
                  {worker.position.replaceAll("_", " ")} · {worker.primary_location ?? "Location pending"}
                </div>
                <div className="mt-2 text-xs text-iron-500">
                  {status?.blockers.join(" ") ||
                    (status
                      ? "Required evidence is complete."
                      : checking
                        ? "Deployment evidence is being verified. This worker is not cleared for deployment."
                        : "Deployment evidence is unverified. This worker is not cleared for deployment.")}
                </div>
              </button>
            );
          })}
        </div>
      </section>

      <form onSubmit={submit} className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
        <h2 className="font-semibold text-iron-950">Record orientation evidence</h2>
        <p className="mt-1 text-sm text-iron-500">
          Saved records are append-only. Corrections require a new record.
        </p>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <Field label="Worker">
            <select required value={selected} onChange={(event) => setSelected(event.target.value)}>
              {workers.map((worker) => (
                <option key={worker.id} value={worker.id}>
                  {worker.legal_first_name} {worker.legal_last_name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Scope">
            <select value={scope} onChange={(event) => setScope(event.target.value as "company" | "site")}>
              <option value="company">Company</option>
              <option value="site">Project / site</option>
            </select>
          </Field>
          {scope === "site" ? (
            <Field label="Site name">
              <input required value={siteName} onChange={(event) => setSiteName(event.target.value)} />
            </Field>
          ) : null}
          <Field label="Trigger">
            <select value={trigger} onChange={(event) => setTrigger(event.target.value)}>
              {[
                "new_hire",
                "new_site",
                "changed_hazards",
                "new_task",
                "unsafe_performance",
                "worker_request",
                "qualification_expiry",
                "refresher",
              ].map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </Field>
          <Field label="Instructor">
            <input required value={instructor} onChange={(event) => setInstructor(event.target.value)} />
          </Field>
          <Field label="Supervisor">
            <input required value={supervisor} onChange={(event) => setSupervisor(event.target.value)} />
          </Field>
          <Field label="Document version">
            <input required value={version} onChange={(event) => setVersion(event.target.value)} />
          </Field>
          <Field label="Competency">
            <select value={competency} onChange={(event) => setCompetency(event.target.value)}>
              <option value="not_assessed">Not assessed</option>
              <option value="requires_supervision">Requires supervision</option>
              <option value="passed">Passed</option>
            </select>
          </Field>
        </div>

        <div className="mt-6 flex flex-wrap items-start justify-between gap-3 border-t border-iron-100 pt-5">
          <div>
            <h3 className="font-semibold text-iron-950">Orientation checklist</h3>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-iron-500">
              Check each topic only after it has been reviewed with the worker. This record does not
              replace supervisor verification of current site conditions.
            </p>
          </div>
          <div className="rounded-full bg-iron-50 px-3 py-1.5 text-sm font-semibold text-iron-700" aria-live="polite">
            {recordedTopicCount} of {orientationTopicCodes.length} topics recorded
          </div>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {orientationTopicCodes.map((code) => {
            const label = topicLabel(code);
            const topic = topics[code];
            const notApplicable = topic.applicability === "not_applicable";

            return (
              <fieldset key={code} className="rounded-md border border-iron-100 p-4">
                <legend className="px-1 text-sm font-semibold text-iron-800">{label}</legend>
                <div className="mt-1 flex flex-wrap gap-x-5 gap-y-2 text-sm font-medium text-iron-700">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      aria-label={`${label} completed`}
                      checked={topic.completed}
                      disabled={notApplicable}
                      onChange={(event) => setTopicCompleted(code, event.target.checked)}
                    />
                    Completed
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      aria-label={`${label} not applicable`}
                      checked={notApplicable}
                      onChange={(event) => setTopicNotApplicable(code, event.target.checked)}
                    />
                    Not applicable
                  </label>
                </div>
                {notApplicable ? (
                  <label className="mt-3 grid gap-1 text-sm font-medium text-iron-700">
                    Reason not applicable
                    <input
                      required
                      aria-label={`${label} not-applicable reason`}
                      value={topic.notApplicableBasis}
                      onChange={(event) =>
                        setTopics((current) => ({
                          ...current,
                          [code]: { ...current[code], notApplicableBasis: event.target.value },
                        }))
                      }
                      className="rounded-md border border-iron-100 px-3 py-2 text-sm"
                    />
                  </label>
                ) : null}
              </fieldset>
            );
          })}
        </div>

        <div className="mt-4 flex flex-wrap gap-5 text-sm font-medium">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={ppe} onChange={(event) => setPpe(event.target.checked)} />
            PPE verified
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={qualifications}
              onChange={(event) => setQualifications(event.target.checked)}
            />
            Qualifications verified
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={ack} onChange={(event) => setAck(event.target.checked)} />
            Worker acknowledged
          </label>
        </div>
        {!topicsReady ? (
          <p className="mt-4 text-sm text-iron-500">
            Record all {orientationTopicCodes.length} orientation topics before saving.
          </p>
        ) : null}
        <button
          disabled={!selected || !topicsReady}
          className="mt-4 rounded-md bg-brand-gold px-4 py-2 text-sm font-semibold text-brand-black disabled:opacity-50"
        >
          Save immutable record
        </button>
      </form>
    </section>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="grid gap-1 text-sm font-medium text-iron-700 [&>input]:rounded-md [&>input]:border [&>input]:px-3 [&>input]:py-2 [&>select]:rounded-md [&>select]:border [&>select]:px-3 [&>select]:py-2">
      {label}
      {children}
    </label>
  );
}

function Status({
  value,
}: {
  value: DeploymentStatus["status"] | "Checking status" | "Status unavailable";
}) {
  const tone =
    value === "Ready"
      ? "bg-emerald-100 text-emerald-800"
      : value === "Blocked" || value === "Status unavailable"
        ? "bg-red-100 text-red-800"
        : "bg-amber-100 text-amber-800";
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${tone}`}>{value}</span>;
}
