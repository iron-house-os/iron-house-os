import {
  ArrowUpRight,
  Bot,
  CheckCircle2,
  CircleAlert,
  CircleHelp,
  ClipboardList,
  Lightbulb,
  Search,
  Send,
  ShieldCheck,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import {
  HelpCoachReply,
  HelpFeedbackEvidence,
  HelpFeedbackType,
  HelpImprovement,
  HelpImprovementStatus,
  helpCoachApi,
} from "../api/helpCoach";
import { useAuth } from "../contexts/AuthContext";
import {
  contextualHelpArticle,
  helpArticlesForUser,
  searchHelpArticles,
  type HelpArticle,
} from "../helpArticles";
import { modulePathWithProjectContext, readEffectiveProjectContext } from "../utils/projectContext";

function ArticleInstructions({ article }: { article: HelpArticle }) {
  return (
    <div className="mt-4 border-t border-iron-100 pt-4">
      <ol className="space-y-3">
        {article.steps.map((step, index) => (
          <li key={step} className="flex gap-3 text-sm leading-6 text-iron-700">
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-brand-gold font-semibold text-brand-black">
              {index + 1}
            </span>
            <span>{step}</span>
          </li>
        ))}
      </ol>
      <div className="mt-4 rounded-lg bg-emerald-50 p-3 text-sm leading-6 text-emerald-900">
        <CheckCircle2 className="mr-2 inline h-4 w-4" aria-hidden="true" />
        <strong>What happens next:</strong> {article.expectedResult}
      </div>
      {article.approvalNote ? (
        <div className="mt-3 rounded-lg bg-amber-50 p-3 text-sm leading-6 text-amber-950">
          <ShieldCheck className="mr-2 inline h-4 w-4" aria-hidden="true" />
          <strong>Important:</strong> {article.approvalNote}
        </div>
      ) : null}
    </div>
  );
}

function ArticleCard({ article, destination }: { article: HelpArticle; destination: string }) {
  return (
    <article className="rounded-xl border border-iron-100 bg-white p-4 shadow-sm sm:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-brand-gold-dark">
            {article.kind === "task" ? "How to" : "Module guide"}
          </div>
          <h3 className="mt-1 text-lg font-semibold text-iron-950">{article.title}</h3>
          <p className="mt-2 text-sm leading-6 text-iron-600">{article.summary}</p>
        </div>
        <Link
          to={destination}
          className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-md border border-brand-gold px-4 text-sm font-semibold text-iron-900 transition hover:bg-brand-gold/10"
        >
          Open page <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
        </Link>
      </div>
      <details className="group mt-4">
        <summary className="flex min-h-11 cursor-pointer list-none items-center rounded-md bg-iron-50 px-4 text-sm font-semibold text-iron-900 transition hover:bg-brand-gold/10">
          <span className="group-open:hidden">Show simple instructions</span>
          <span className="hidden group-open:inline">Hide instructions</span>
        </summary>
        <ArticleInstructions article={article} />
      </details>
    </article>
  );
}

const feedbackOptions: Array<{
  type: HelpFeedbackType;
  label: string;
  icon: typeof ThumbsUp;
}> = [
  { type: "helpful", label: "This helped", icon: ThumbsUp },
  { type: "not_helpful", label: "Not quite", icon: ThumbsDown },
  { type: "stuck", label: "I’m stuck", icon: CircleAlert },
  { type: "suggestion", label: "Suggest an improvement", icon: Lightbulb },
];

function HelpFeedbackControls({
  route,
  projectName,
  sourceIds,
}: {
  route: string;
  projectName?: string;
  sourceIds: string[];
}) {
  const [selected, setSelected] = useState<HelpFeedbackType | null>(null);
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submitFeedback(feedbackType: HelpFeedbackType) {
    if (submitting || (feedbackType === "suggestion" && !note.trim())) return;
    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      const receipt = await helpCoachApi.submitFeedback({
        feedbackType,
        route,
        projectName,
        sourceIds,
        note,
      });
      setMessage(receipt.message);
      setSelected(null);
      setNote("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Help feedback could not be recorded.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mt-5 border-t border-iron-200 pt-5" aria-labelledby="help-feedback-heading">
      <h3 id="help-feedback-heading" className="text-base font-semibold text-iron-950">
        Did this Help work for you?
      </h3>
      <p className="mt-1 text-sm leading-6 text-iron-600">
        Your feedback goes to management for review. It never changes the OS automatically.
      </p>
      <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {feedbackOptions.map((option) => {
          const Icon = option.icon;
          return (
            <button
              key={option.type}
              type="button"
              aria-pressed={selected === option.type}
              onClick={() => {
                setMessage(null);
                setError(null);
                if (option.type === "helpful") void submitFeedback(option.type);
                else setSelected(option.type);
              }}
              disabled={submitting}
              className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg border border-iron-200 bg-white px-3 text-sm font-semibold text-iron-900 transition hover:border-brand-gold hover:bg-brand-gold/10 disabled:cursor-not-allowed disabled:opacity-60 aria-pressed:border-brand-gold aria-pressed:bg-brand-gold/10"
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {option.label}
            </button>
          );
        })}
      </div>

      {selected && selected !== "helpful" ? (
        <div className="mt-4 rounded-lg border border-iron-200 bg-white p-4">
          <label htmlFor="help-feedback-note" className="text-sm font-semibold text-iron-900">
            {selected === "suggestion" ? "What would you improve?" : "What was unclear? (optional)"}
          </label>
          <textarea
            id="help-feedback-note"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            rows={3}
            maxLength={600}
            placeholder={selected === "suggestion" ? "Use plain words. For example: Show where my saved form went." : "Add a short note if it will help management understand."}
            className="mt-2 min-h-20 w-full resize-y rounded-lg border border-iron-200 bg-iron-50 px-4 py-3 text-base text-iron-950 outline-none focus:border-brand-gold focus:ring-2 focus:ring-brand-gold/30"
          />
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void submitFeedback(selected)}
              disabled={submitting || (selected === "suggestion" && !note.trim())}
              className="inline-flex min-h-11 items-center justify-center rounded-lg bg-iron-950 px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-iron-300"
            >
              {submitting ? "Recording…" : "Send to management"}
            </button>
            <button
              type="button"
              onClick={() => { setSelected(null); setNote(""); }}
              className="min-h-11 rounded-lg px-4 text-sm font-semibold text-iron-700 underline"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}

      {message ? <div role="status" className="mt-3 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-900">{message}</div> : null}
      {error ? <div role="alert" className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-950">{error}</div> : null}
      <p className="mt-3 text-xs leading-5 text-iron-500">
        Do not include passwords, SINs, banking, medical, payroll, disciplinary or restricted first-aid information.
      </p>
    </div>
  );
}

const feedbackLabels: Record<HelpFeedbackType, string> = {
  helpful: "Help worked",
  not_helpful: "Help did not answer it",
  stuck: "Employee is stuck",
  suggestion: "Workflow suggestion",
};

function ImprovementInbox() {
  const [items, setItems] = useState<HelpImprovement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, { status: HelpImprovementStatus; note: string }>>({});
  const [savingId, setSavingId] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<Record<string, HelpFeedbackEvidence[] | undefined>>({});
  const [evidenceLoadingId, setEvidenceLoadingId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    helpCoachApi.listImprovements()
      .then((result) => {
        if (!active) return;
        setItems(result.items);
        setDrafts(Object.fromEntries(result.items.map((item) => [item.id, {
          status: item.status,
          note: item.review_note ?? "",
        }])));
      })
      .catch((reason) => {
        if (active) setError(reason instanceof Error ? reason.message : "The Improvement Inbox is unavailable.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  async function save(item: HelpImprovement) {
    const draft = drafts[item.id] ?? { status: item.status, note: item.review_note ?? "" };
    setSavingId(item.id);
    setError(null);
    try {
      const updated = await helpCoachApi.updateImprovement(item.id, draft.status, draft.note);
      setItems((current) => current.map((entry) => entry.id === updated.id ? updated : entry));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The review status could not be saved.");
    } finally {
      setSavingId(null);
    }
  }

  async function toggleEvidence(item: HelpImprovement) {
    if (evidence[item.id]) {
      setEvidence((current) => ({ ...current, [item.id]: undefined }));
      return;
    }
    setEvidenceLoadingId(item.id);
    setError(null);
    try {
      const result = await helpCoachApi.listImprovementEvidence(item.id);
      setEvidence((current) => ({ ...current, [item.id]: result.items }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The feedback reports could not be loaded.");
    } finally {
      setEvidenceLoadingId(null);
    }
  }

  return (
    <section className="rounded-xl border border-brand-gold/40 bg-white p-4 shadow-sm sm:p-6" aria-labelledby="improvement-inbox-heading">
      <div className="flex items-start gap-3">
        <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-iron-950 text-brand-gold">
          <ClipboardList className="h-6 w-6" aria-hidden="true" />
        </div>
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-brand-gold-dark">Management only</div>
          <h2 id="improvement-inbox-heading" className="mt-1 text-xl font-semibold text-iron-950">Improvement Inbox</h2>
          <p className="mt-1 text-sm leading-6 text-iron-600">
            Review repeated Help problems and suggestions. Planning an item does not change a workflow or approve a build.
          </p>
        </div>
      </div>

      {loading ? <p className="mt-4 text-sm text-iron-500">Loading improvement signals…</p> : null}
      {error ? <div role="alert" className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-950">{error}</div> : null}
      {!loading && !items.length ? (
        <div className="mt-4 rounded-lg border border-dashed border-iron-200 bg-iron-50 p-4 text-sm text-iron-600">
          No Help feedback has been recorded yet.
        </div>
      ) : null}
      <div className="mt-4 space-y-3">
        {items.map((item) => {
          const draft = drafts[item.id] ?? { status: item.status, note: item.review_note ?? "" };
          return (
            <article key={item.id} className="rounded-xl border border-iron-100 bg-iron-50 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-iron-950">{feedbackLabels[item.feedback_type]}</h3>
                  <p className="mt-1 text-sm text-iron-600">
                    {item.evidence_count} {item.evidence_count === 1 ? "report" : "reports"} · {item.route || "/help"}
                  </p>
                </div>
                <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold uppercase tracking-wide text-iron-700">
                  {item.status}
                </span>
              </div>
              {item.latest_project_name ? <p className="mt-3 text-sm text-iron-700"><strong>Latest project:</strong> {item.latest_project_name}</p> : null}
              {item.latest_note ? <p className="mt-2 rounded-lg bg-white p-3 text-sm leading-6 text-iron-800">{item.latest_note}</p> : null}
              <p className="mt-2 text-xs text-iron-500">Last reported {new Date(item.last_seen_at).toLocaleDateString("en-CA")}</p>
              <button
                type="button"
                onClick={() => void toggleEvidence(item)}
                className="mt-3 min-h-11 rounded-lg px-3 text-sm font-semibold text-iron-700 underline"
              >
                {evidenceLoadingId === item.id
                  ? "Loading reports…"
                  : evidence[item.id]
                    ? "Hide individual reports"
                    : `Show ${item.evidence_count} individual ${item.evidence_count === 1 ? "report" : "reports"}`}
              </button>
              {evidence[item.id] ? (
                <div className="mt-2 space-y-2" aria-label="Individual Help feedback reports">
                  {evidence[item.id]?.map((entry) => (
                    <div key={entry.id} className="rounded-lg border border-iron-200 bg-white p-3 text-sm text-iron-700">
                      <div className="text-xs font-semibold uppercase tracking-wide text-iron-500">
                        {entry.audience} · {new Date(entry.created_at).toLocaleDateString("en-CA")}
                      </div>
                      {entry.project_name ? <div className="mt-1"><strong>Project:</strong> {entry.project_name}</div> : null}
                      <div className="mt-1">{entry.note || "No note was included."}</div>
                    </div>
                  ))}
                </div>
              ) : null}
              <div className="mt-4 grid gap-3 md:grid-cols-[180px_1fr_auto] md:items-end">
                <label className="text-sm font-semibold text-iron-900">
                  Review status
                  <select
                    value={draft.status}
                    onChange={(event) => setDrafts((current) => ({
                      ...current,
                      [item.id]: { ...draft, status: event.target.value as HelpImprovementStatus },
                    }))}
                    className="mt-2 min-h-11 w-full rounded-lg border border-iron-200 bg-white px-3 text-sm"
                  >
                    <option value="new">New</option>
                    <option value="reviewing">Reviewing</option>
                    <option value="planned">Planned</option>
                    <option value="dismissed">Dismissed</option>
                  </select>
                </label>
                <label className="text-sm font-semibold text-iron-900">
                  Management note (optional)
                  <input
                    value={draft.note}
                    onChange={(event) => setDrafts((current) => ({
                      ...current,
                      [item.id]: { ...draft, note: event.target.value },
                    }))}
                    maxLength={600}
                    className="mt-2 min-h-11 w-full rounded-lg border border-iron-200 bg-white px-3 text-sm"
                  />
                </label>
                <button
                  type="button"
                  onClick={() => void save(item)}
                  disabled={savingId === item.id}
                  className="min-h-11 rounded-lg bg-iron-950 px-4 text-sm font-semibold text-white disabled:bg-iron-300"
                >
                  {savingId === item.id ? "Saving…" : "Save review"}
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

export function HelpCenterPage() {
  const { user, portalRole } = useAuth();
  const location = useLocation();
  const [query, setQuery] = useState("");
  const [coachDraft, setCoachDraft] = useState("");
  const [coachQuestion, setCoachQuestion] = useState("");
  const [coachReply, setCoachReply] = useState<HelpCoachReply | null>(null);
  const [coachError, setCoachError] = useState<string | null>(null);
  const [coachLoading, setCoachLoading] = useState(false);
  const projectContext = readEffectiveProjectContext(location.search);
  const sourcePath = new URLSearchParams(location.search).get("from") ?? "";
  const articles = useMemo(
    () => (user ? helpArticlesForUser(user.role, portalRole) : []),
    [portalRole, user],
  );
  const contextArticle = useMemo(
    () => contextualHelpArticle(sourcePath, articles),
    [articles, sourcePath],
  );
  const results = useMemo(() => searchHelpArticles(articles, query), [articles, query]);
  const featured = articles.filter((article) => article.featured).slice(0, 6);
  const projectName = projectContext.projectName;
  const isManagement = user?.role === "admin" || user?.role === "operations_manager";
  const feedbackSourceIds = coachReply?.sources.map((source) => source.id)
    ?? (contextArticle ? [contextArticle.id] : []);

  async function askCoach(event: FormEvent) {
    event.preventDefault();
    const question = coachDraft.trim();
    if (!question || coachLoading) return;
    setCoachLoading(true);
    setCoachError(null);
    setCoachReply(null);
    setCoachQuestion(question);
    try {
      setCoachReply(await helpCoachApi.send(question, { route: sourcePath, projectName: projectName ?? undefined }));
      setCoachDraft("");
    } catch (reason) {
      setCoachError(reason instanceof Error ? reason.message : "The Help Coach is unavailable.");
    } finally {
      setCoachLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="ihos-brand-surface overflow-hidden rounded-xl border border-brand-gold/30 px-5 py-6 text-white shadow-brand sm:px-7">
        <div className="flex items-start gap-4">
          <div className="grid h-12 w-12 shrink-0 place-items-center rounded-xl border border-brand-gold/40 bg-white/10 text-brand-gold">
            <CircleHelp className="h-7 w-7" aria-hidden="true" />
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-gold">Iron House Help</div>
            <h1 className="mt-2 text-3xl font-semibold text-brand-silver">What do you need to do?</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-100">
              Find simple, role-appropriate instructions. Each guide explains the steps, the result and whether another person must approve it.
            </p>
            {projectName ? (
              <div className="mt-3 inline-flex rounded-full border border-brand-gold/40 bg-white/10 px-3 py-1 text-xs font-semibold text-brand-silver">
                Active project: {projectName}
              </div>
            ) : null}
          </div>
        </div>
      </section>

      {contextArticle ? (
        <section className="rounded-xl border-2 border-brand-gold bg-white p-4 shadow-sm sm:p-6" aria-labelledby="current-page-help">
          <div className="text-xs font-semibold uppercase tracking-wide text-brand-gold-dark">Help with the page you were on</div>
          <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 id="current-page-help" className="text-xl font-semibold text-iron-950">{contextArticle.title}</h2>
              <p className="mt-2 text-sm leading-6 text-iron-600">{contextArticle.summary}</p>
            </div>
            <Link
              to={modulePathWithProjectContext(contextArticle.path, projectContext)}
              className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-md bg-brand-gold px-4 text-sm font-semibold text-brand-black transition hover:bg-brand-gold-light"
            >
              Return to task <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
          <ArticleInstructions article={contextArticle} />
        </section>
      ) : null}

      <section className="rounded-xl border border-brand-gold/40 bg-white p-4 shadow-sm sm:p-6" aria-labelledby="help-coach-heading">
        <div className="flex items-start gap-3">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-iron-950 text-brand-gold">
            <Bot className="h-6 w-6" aria-hidden="true" />
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-brand-gold-dark">Read-only guidance</div>
            <h2 id="help-coach-heading" className="mt-1 text-xl font-semibold text-iron-950">Ask the Help Coach</h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-iron-600">
              Type what you are trying to do. The Coach uses only approved instructions for your access level and cannot change, submit, approve or send anything.
            </p>
          </div>
        </div>

        <form onSubmit={(event) => void askCoach(event)} className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="min-w-0 flex-1" htmlFor="help-coach-question">
            <span className="mb-2 block text-sm font-semibold text-iron-900">What do you need help with?</span>
            <textarea
              id="help-coach-question"
              value={coachDraft}
              onChange={(event) => setCoachDraft(event.target.value)}
              rows={2}
              maxLength={1000}
              placeholder="For example: How do I enter my time?"
              className="min-h-14 w-full resize-y rounded-lg border border-iron-200 bg-iron-50 px-4 py-3 text-base text-iron-950 outline-none transition placeholder:text-iron-400 focus:border-brand-gold focus:ring-2 focus:ring-brand-gold/30"
            />
          </label>
          <button
            type="submit"
            disabled={coachLoading || !coachDraft.trim()}
            className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-iron-950 px-5 text-sm font-semibold text-white transition hover:bg-iron-800 disabled:cursor-not-allowed disabled:bg-iron-300"
          >
            <Send className="h-4 w-4" aria-hidden="true" />
            {coachLoading ? "Checking Help…" : "Ask Coach"}
          </button>
        </form>

        {coachError ? (
          <div role="alert" className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
            {coachError} Use Search Help below while the Coach is unavailable.
          </div>
        ) : null}

        {coachReply ? (
          <div className="mt-5 rounded-xl border border-iron-100 bg-iron-50 p-4" aria-live="polite">
            <div className="text-xs font-semibold uppercase tracking-wide text-iron-500">Your question</div>
            <div className="mt-1 font-semibold text-iron-950">{coachQuestion}</div>
            <div className="mt-4 text-xs font-semibold uppercase tracking-wide text-brand-gold-dark">
              {coachReply.status === "completed" ? "Grounded Help Coach answer" : "Approved built-in guidance"}
            </div>
            <div className="mt-2 whitespace-pre-wrap text-sm leading-6 text-iron-800">{coachReply.answer}</div>
            {coachReply.sources.length ? (
              <div className="mt-4 border-t border-iron-200 pt-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-iron-500">Approved sources</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {coachReply.sources.map((source) => (
                    <Link
                      key={source.id}
                      to={modulePathWithProjectContext(source.path, projectContext)}
                      className="inline-flex min-h-11 items-center gap-2 rounded-md border border-brand-gold/50 bg-white px-3 text-sm font-semibold text-iron-900 hover:bg-brand-gold/10"
                    >
                      {source.title} <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
                    </Link>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}

        <HelpFeedbackControls
          route={sourcePath}
          projectName={projectName ?? undefined}
          sourceIds={feedbackSourceIds}
        />

        <p className="mt-4 text-xs leading-5 text-iron-500">
          Do not enter passwords, SINs, banking, medical, payroll, disciplinary or restricted first-aid information. Stop work and contact your supervisor whenever conditions are unsafe or unclear.
        </p>
      </section>

      {isManagement ? <ImprovementInbox /> : null}

      <section className="rounded-xl border border-iron-100 bg-white p-4 shadow-sm sm:p-6" aria-labelledby="help-search-heading">
        <h2 id="help-search-heading" className="text-xl font-semibold text-iron-950">Search Help</h2>
        <p className="mt-1 text-sm text-iron-500">Use everyday words such as “time,” “receipt,” “FLHA,” “PO,” “quote” or “equipment.”</p>
        <label className="relative mt-4 block">
          <span className="sr-only">What are you trying to do?</span>
          <Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-iron-400" aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="What are you trying to do?"
            className="min-h-12 w-full rounded-lg border border-iron-200 bg-iron-50 py-3 pl-12 pr-4 text-base text-iron-950 outline-none transition placeholder:text-iron-400 focus:border-brand-gold focus:ring-2 focus:ring-brand-gold/30"
          />
        </label>
      </section>

      {!query && featured.length ? (
        <section aria-labelledby="quick-start-heading">
          <h2 id="quick-start-heading" className="text-xl font-semibold text-iron-950">Common tasks</h2>
          <p className="mt-1 text-sm text-iron-500">Choose what you are trying to do.</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {featured.map((article) => (
              <button
                key={article.id}
                type="button"
                onClick={() => setQuery(article.title)}
                className="min-h-20 rounded-xl border border-brand-gold/40 bg-white p-4 text-left shadow-sm transition hover:border-brand-gold hover:bg-brand-gold/10"
              >
                <span className="font-semibold text-iron-950">{article.title}</span>
                <span className="mt-1 block text-sm text-iron-500">{article.task}</span>
              </button>
            ))}
          </div>
        </section>
      ) : null}

      <section aria-live="polite" aria-labelledby="help-results-heading">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 id="help-results-heading" className="text-xl font-semibold text-iron-950">
              {query ? "Search results" : "All instructions"}
            </h2>
            <p className="mt-1 text-sm text-iron-500">
              {results.length} {results.length === 1 ? "guide" : "guides"} available for your access level.
            </p>
          </div>
          {query ? (
            <button type="button" onClick={() => setQuery("")} className="min-h-11 rounded-md px-3 text-sm font-semibold text-iron-700 underline">
              Clear search
            </button>
          ) : null}
        </div>
        {results.length ? (
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            {results.map((article) => (
              <ArticleCard
                key={article.id}
                article={article}
                destination={modulePathWithProjectContext(article.path, projectContext)}
              />
            ))}
          </div>
        ) : (
          <div className="mt-4 rounded-xl border border-dashed border-iron-200 bg-white p-6 text-center">
            <div className="font-semibold text-iron-950">No guide matched those words.</div>
            <p className="mt-2 text-sm text-iron-500">Try a shorter search or ask your supervisor. Help does not replace a required approval.</p>
          </div>
        )}
      </section>
    </div>
  );
}
