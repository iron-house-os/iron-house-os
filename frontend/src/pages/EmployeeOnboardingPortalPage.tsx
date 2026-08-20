import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, ShieldCheck } from "lucide-react";
import { useParams } from "react-router-dom";

import {
  employeeOnboardingApi,
  OnboardingRecord,
  requiredOnboardingItems,
} from "../api/employeeOnboarding";

export function EmployeeOnboardingPortalPage() {
  const { token = "" } = useParams();
  const [record, setRecord] = useState<OnboardingRecord | null>(null);
  const [completed, setCompleted] = useState<string[]>([]);
  const [acknowledged, setAcknowledged] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const onboarding = await employeeOnboardingApi.portalRecord(token);
      setRecord(onboarding);
      setCompleted(
        requiredOnboardingItems
          .filter(([code]) => !onboarding.missing_items.includes(code))
          .map(([code]) => code),
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Invitation is invalid, revoked, or expired.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  async function saveProgress() {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await employeeOnboardingApi.savePortalProgress(token, completed);
      setRecord(updated);
      setMessage("Progress saved. You may safely return using the same invitation before it expires.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to save progress.");
    } finally {
      setSaving(false);
    }
  }

  async function submit() {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await employeeOnboardingApi.submitPortal(token, completed, acknowledged);
      setRecord(updated);
      setMessage("Onboarding submitted for management review. Submission does not activate employment or site deployment.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to submit onboarding.");
    } finally {
      setSaving(false);
    }
  }

  const complete = completed.length === requiredOnboardingItems.length;
  const submitted = record ? ["submitted", "approved", "active"].includes(record.status) : false;

  return (
    <main className="min-h-screen bg-iron-50 px-4 py-8 text-iron-950 sm:py-12">
      <div className="mx-auto max-w-3xl space-y-6">
        <header className="ihos-brand-surface rounded-xl border border-brand-gold/30 px-6 py-6 text-white shadow-brand">
          <div className="flex items-start gap-4">
            <div className="grid h-12 w-12 place-items-center rounded-xl border border-brand-gold/40 bg-white/10 text-brand-gold">
              <ShieldCheck />
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-gold">Iron House Contracting</div>
              <h1 className="mt-2 text-3xl font-semibold text-brand-silver">Employee onboarding</h1>
              <p className="mt-2 text-sm leading-6 text-iron-100">Secure, time-limited new-hire completion portal.</p>
            </div>
          </div>
        </header>

        {loading ? <div role="status" className="rounded-xl border border-iron-100 bg-white p-5 text-sm shadow-sm">Opening secure invitation…</div> : null}
        {error ? <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
        {message ? <div role="status" className="rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">{message}</div> : null}

        {record ? (
          <section className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold text-iron-950">Welcome, {record.preferred_name || record.legal_first_name}</h2>
                <p className="mt-1 text-sm text-iron-500">{labelValue(record.position)} · start date {record.start_date}</p>
              </div>
              <span className="rounded-full bg-iron-100 px-3 py-1.5 text-sm font-semibold text-iron-700">{completed.length} of {requiredOnboardingItems.length}</span>
            </div>

            {record.correction_note ? <p className="mt-4 rounded-md bg-amber-50 p-3 text-sm text-amber-900">Management correction request: {record.correction_note}</p> : null}

            {submitted ? (
              <div className="mt-5 flex items-start gap-3 rounded-md border border-emerald-200 bg-emerald-50 p-4 text-emerald-900">
                <CheckCircle2 className="mt-0.5 h-5 w-5" />
                <div><div className="font-semibold">Submitted for review</div><p className="mt-1 text-sm">Management must still approve the record and complete all deployment controls before activation.</p></div>
              </div>
            ) : (
              <>
                <p className="mt-5 text-sm leading-6 text-iron-600">
                  Check an item only after the information or document has been provided through the approved Iron House process. Do not enter banking, tax, identity-document, or medical details on this checklist.
                </p>
                <fieldset className="mt-4 grid gap-3">
                  <legend className="sr-only">Required onboarding items</legend>
                  {requiredOnboardingItems.map(([code, label]) => (
                    <label key={code} className="flex items-start gap-3 rounded-md border border-iron-100 p-3 text-sm font-medium text-iron-800">
                      <input
                        type="checkbox"
                        className="mt-0.5"
                        checked={completed.includes(code)}
                        onChange={(event) => setCompleted((current) => event.target.checked ? [...current, code] : current.filter((item) => item !== code))}
                      />
                      {label}
                    </label>
                  ))}
                </fieldset>
                <label className="mt-5 flex items-start gap-3 rounded-md bg-iron-50 p-4 text-sm font-medium text-iron-800">
                  <input type="checkbox" className="mt-0.5" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} />
                  I confirm the checked items are complete and the information I provided is accurate to the best of my knowledge.
                </label>
                <div className="mt-5 flex flex-wrap gap-3">
                  <button type="button" disabled={saving} onClick={() => void saveProgress()} className="rounded-md border border-brand-gold/50 px-4 py-2 text-sm font-semibold text-iron-800 disabled:opacity-50">Save progress</button>
                  <button type="button" disabled={saving || !complete || !acknowledged} onClick={() => void submit()} className="rounded-md bg-brand-gold px-4 py-2 text-sm font-semibold text-brand-black disabled:opacity-50">Submit for review</button>
                </div>
              </>
            )}
          </section>
        ) : null}
      </div>
    </main>
  );
}

function labelValue(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
