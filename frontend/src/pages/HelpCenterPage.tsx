import { ArrowUpRight, CheckCircle2, CircleHelp, Search, ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";

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

export function HelpCenterPage() {
  const { user, portalRole } = useAuth();
  const location = useLocation();
  const [query, setQuery] = useState("");
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
