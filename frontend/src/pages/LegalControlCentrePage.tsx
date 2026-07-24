import { AlertTriangle, CheckCircle2, Scale } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { legalApi, LegalDashboard, LegalMatterDetail } from "../api/legal";

export function LegalControlCentrePage() {
  const [dashboard, setDashboard] = useState<LegalDashboard | null>(null);
  const [selected, setSelected] = useState<LegalMatterDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadDashboard() {
    setError(null);
    try { setDashboard(await legalApi.dashboard()); }
    catch (current) { setError(current instanceof Error ? current.message : "Unable to load legal control."); }
  }
  async function openMatter(id: string) {
    setError(null);
    try { setSelected(await legalApi.matter(id)); }
    catch (current) { setError(current instanceof Error ? current.message : "Unable to open matter."); }
  }
  useEffect(() => { void loadDashboard(); }, []);

  async function createMatter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(null);
    const data = new FormData(event.currentTarget);
    try {
      const matter = await legalApi.createMatter({
        title: data.get("title"), matter_type: data.get("matter_type"), project_name: data.get("project_name") || null,
        counterparty: data.get("counterparty") || null, description: data.get("description"),
        confidentiality: data.get("confidentiality"), jurisdiction: "British Columbia, Canada",
      });
      event.currentTarget.reset(); await loadDashboard(); await openMatter(matter.id);
    } catch (current) { setError(current instanceof Error ? current.message : "Unable to create matter."); }
    finally { setBusy(false); }
  }
  async function analyse() {
    if (!selected) return; setBusy(true); setError(null);
    try { await legalApi.analyse(selected.id); await openMatter(selected.id); }
    catch (current) { setError(current instanceof Error ? current.message : "Unable to analyse matter."); }
    finally { setBusy(false); }
  }
  async function addDeadline(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!selected) return; setBusy(true); setError(null);
    const data = new FormData(event.currentTarget);
    try {
      await legalApi.createDeadline(selected.id, { title: data.get("title"), due_date: data.get("due_date"), source_basis: data.get("source_basis") });
      event.currentTarget.reset(); await openMatter(selected.id); await loadDashboard();
    } catch (current) { setError(current instanceof Error ? current.message : "Unable to add deadline."); }
    finally { setBusy(false); }
  }
  async function verifyDeadline(id: string) {
    const evidence = window.prompt("Enter the reviewed source, contract clause, or counsel confirmation:");
    if (!evidence || !selected) return; setBusy(true); setError(null);
    try { await legalApi.verifyDeadline(id, evidence); await openMatter(selected.id); await loadDashboard(); }
    catch (current) { setError(current instanceof Error ? current.message : "Unable to verify deadline."); }
    finally { setBusy(false); }
  }

  return <section className="space-y-6">
    <header className="ihos-brand-surface rounded-xl border border-brand-gold/30 p-6 text-white shadow-brand">
      <div className="flex items-center gap-3"><Scale className="h-7 w-7 text-brand-gold" /><div><div className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-gold">Build 230</div><h1 className="text-3xl font-semibold text-brand-silver">AI Legal Control Centre</h1></div></div>
      <p className="mt-3 max-w-4xl text-sm text-iron-100">Supervised construction-law issue spotting, contract drafting support, risk recommendations, source control and verified deadline tracking.</p>
    </header>
    <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
      <div className="flex gap-2"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /><div><strong>Human approval gate.</strong> Drafts are not final legal opinions. Qualified counsel must review privileged matters, contract execution, notices, filings, settlements, waivers, discipline and termination.</div></div>
    </div>
    {error ? <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
    <div className="grid gap-6 xl:grid-cols-[390px_1fr]">
      <form onSubmit={createMatter} className="space-y-3 rounded-xl border bg-white p-5">
        <h2 className="font-semibold">Open legal matter</h2>
        <input required name="title" placeholder="Matter title" className="w-full rounded-md border p-2 text-sm" />
        <select name="matter_type" className="w-full rounded-md border p-2 text-sm"><option>Contract review</option><option>Contract drafting</option><option>Builders lien / payment</option><option>Tender / procurement</option><option>Employment</option><option>WorkSafeBC / OHS</option><option>Claim / dispute</option><option>Privacy / AI</option><option>Environmental / heritage</option><option>Transportation / fleet</option></select>
        <input name="project_name" placeholder="Project (optional)" className="w-full rounded-md border p-2 text-sm" />
        <input name="counterparty" placeholder="Counterparty (optional)" className="w-full rounded-md border p-2 text-sm" />
        <textarea required minLength={10} name="description" placeholder="Facts, requested review and business objective" className="h-32 w-full rounded-md border p-2 text-sm" />
        <label className="block text-xs font-semibold text-iron-600">Information class<select name="confidentiality" className="mt-1 w-full rounded-md border p-2 text-sm font-normal"><option value="standard">Standard business information</option><option value="personal_information">Contains personal information — block AI</option><option value="privilege_requested">Privilege requested — block AI</option></select></label>
        <button disabled={busy} className="w-full rounded-md bg-brand-gold p-2 text-sm font-semibold text-brand-black disabled:opacity-50">Open matter</button>
      </form>
      <div className="space-y-4">
        <div className="rounded-xl border bg-white p-5"><div className="flex items-center justify-between"><h2 className="font-semibold">Matter register</h2><span className="text-xs text-iron-500">{dashboard?.candidate_deadline_count ?? 0} candidate deadlines</span></div>
          <div className="mt-3 space-y-2">{dashboard?.matters.length ? dashboard.matters.map((matter) => <button key={matter.id} onClick={() => void openMatter(matter.id)} className="w-full rounded-lg border p-3 text-left hover:border-brand-gold"><div className="font-semibold">{matter.title}</div><div className="mt-1 text-xs text-iron-500">{matter.matter_type} · {matter.risk_level} · {matter.assigned_specialists.length} specialists</div></button>) : <p className="text-sm text-iron-500">No legal matters recorded.</p>}</div>
        </div>
        {selected ? <MatterPanel matter={selected} busy={busy} analyse={analyse} addDeadline={addDeadline} verifyDeadline={verifyDeadline} /> : null}
      </div>
    </div>
    <div className="grid gap-6 lg:grid-cols-2">
      <Register title="Integrated specialist roster" items={dashboard?.specialists.map((item) => <div key={item.key} className="rounded-lg border p-3"><div className="font-semibold">{item.name}</div><p className="mt-1 text-sm text-iron-500">{item.mandate}</p></div>) ?? []} />
      <Register title="Controlled authority register" items={dashboard?.authorities.map((item) => <a key={item.id} href={item.url} target="_blank" rel="noreferrer" className="block rounded-lg border p-3 hover:border-brand-gold"><div className="flex justify-between gap-2"><span className="font-semibold">{item.title}</span><span className={item.status === "active" ? "text-emerald-700" : "text-red-700"}>{item.status.replaceAll("_", " ")}</span></div><div className="mt-1 text-xs text-iron-500">{item.jurisdiction} · {item.id}</div></a>) ?? []} />
    </div>
  </section>;
}

function MatterPanel({ matter, busy, analyse, addDeadline, verifyDeadline }: { matter: LegalMatterDetail; busy: boolean; analyse: () => Promise<void>; addDeadline: (event: FormEvent<HTMLFormElement>) => Promise<void>; verifyDeadline: (id: string) => Promise<void> }) {
  return <div className="space-y-4 rounded-xl border bg-white p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="text-xs font-semibold uppercase text-brand-gold-dark">{matter.matter_type}</div><h2 className="text-xl font-semibold">{matter.title}</h2><p className="mt-2 text-sm text-iron-600">{matter.description}</p></div><button disabled={busy || matter.confidentiality !== "standard"} onClick={() => void analyse()} className="rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">Create source-backed AI draft</button></div>
    <div className="flex flex-wrap gap-2">{matter.assigned_specialists.map((key) => <span key={key} className="rounded-full bg-iron-100 px-3 py-1 text-xs">{key.replaceAll("_", " ")}</span>)}</div>
    {matter.analyses.map((analysis) => <article key={analysis.id} className="rounded-lg border border-brand-gold/40 p-4"><div className="flex items-center gap-2 text-sm font-semibold"><CheckCircle2 className="h-4 w-4 text-brand-gold-dark" />Draft analysis · human review required</div><p className="mt-3 text-sm">{analysis.executive_summary}</p>{analysis.draft_text ? <div className="mt-4 rounded-md bg-iron-50 p-4"><h3 className="text-sm font-semibold">Lawyer-ready draft work product</h3><pre className="mt-2 whitespace-pre-wrap font-sans text-sm text-iron-700">{analysis.draft_text}</pre></div> : null}<h3 className="mt-4 text-sm font-semibold">Recommendations</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{analysis.recommendations.map((item, index) => <li key={index}>{item.action} <span className="text-iron-500">({item.urgency ?? "review"})</span></li>)}</ul><p className="mt-4 text-xs text-iron-500">{analysis.disclaimer}</p></article>)}
    <form onSubmit={addDeadline} className="grid gap-2 border-t pt-4 md:grid-cols-3"><input required name="title" placeholder="Candidate deadline" className="rounded-md border p-2 text-sm" /><input required type="date" name="due_date" className="rounded-md border p-2 text-sm" /><input required name="source_basis" placeholder="Source / clause / calculation basis" className="rounded-md border p-2 text-sm" /><button disabled={busy} className="rounded-md bg-brand-gold p-2 text-sm font-semibold md:col-span-3">Add candidate — requires verification</button></form>
    {matter.deadlines.map((deadline) => <div key={deadline.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3 text-sm"><div><div className="font-semibold">{deadline.title} · {deadline.due_date}</div><div className="text-xs text-iron-500">{deadline.source_basis}</div></div>{deadline.status === "candidate" ? <button onClick={() => void verifyDeadline(deadline.id)} className="rounded-md border px-3 py-1 font-semibold">Verify with evidence</button> : <span className="font-semibold text-emerald-700">Verified</span>}</div>)}
  </div>;
}
function Register({ title, items }: { title: string; items: React.ReactNode[] }) { return <section className="rounded-xl border bg-white p-5"><h2 className="font-semibold">{title}</h2><div className="mt-3 space-y-2">{items}</div></section>; }
