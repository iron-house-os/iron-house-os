import { BookOpenCheck, ExternalLink, HardHat, ShieldCheck, TriangleAlert } from "lucide-react";

const SAFETY_PROGRAM_URL =
  "https://docs.google.com/document/d/1ApKQs4xIR8axW0lIaeqqATDVaZWs1jvSzaZwYK6wUNw/edit?usp=drivesdk";

export function EmployeePortalPage() {
  return (
    <section className="space-y-6">
      <div className="ihos-brand-surface overflow-hidden rounded-xl border border-brand-gold/30 px-6 py-6 text-white shadow-brand">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-4">
            <div className="grid h-16 w-16 shrink-0 place-items-center rounded-2xl border border-brand-gold/40 bg-white/10">
              <HardHat className="h-8 w-8 text-brand-gold" aria-hidden="true" />
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-gold">
                Iron House Contracting
              </div>
              <h1 className="mt-2 text-3xl font-semibold text-brand-silver">Employee Portal</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-100">
                Company safety information and controlled resources for every Iron House employee.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <article className="rounded-xl border border-brand-gold/40 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex gap-4">
              <div className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-brand-gold/15">
                <BookOpenCheck className="h-6 w-6 text-iron-950" aria-hidden="true" />
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-gold-dark">
                  Controlled document
                </div>
                <h2 className="mt-1 text-xl font-semibold text-iron-950">
                  Occupational Health, Safety &amp; Environmental Program
                </h2>
                <p className="mt-2 text-sm leading-6 text-iron-600">
                  Revision 1.1 incorporates current British Columbia and applicable federal safety requirements.
                  Always use this portal link so you are reading the latest controlled version.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <ResourceFact label="Jurisdiction" value="British Columbia" />
            <ResourceFact label="Current revision" value="1.1" />
            <ResourceFact label="Reviewed" value="July 21, 2026" />
          </div>

          <a
            href={SAFETY_PROGRAM_URL}
            target="_blank"
            rel="noreferrer"
            className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-md bg-brand-gold px-4 py-3 text-sm font-semibold text-brand-black transition hover:bg-brand-gold-light sm:w-auto"
          >
            Open Safety Program
            <ExternalLink className="h-4 w-4" aria-hidden="true" />
          </a>
        </article>

        <aside className="space-y-4">
          <div className="rounded-xl border border-iron-100 bg-white p-5">
            <div className="flex items-center gap-3">
              <ShieldCheck className="h-5 w-5 text-brand-gold-dark" aria-hidden="true" />
              <h2 className="font-semibold text-iron-950">Employee responsibilities</h2>
            </div>
            <ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-6 text-iron-600">
              <li>Review the program and follow site-specific procedures.</li>
              <li>Complete required orientations, training and hazard assessments.</li>
              <li>Report hazards, incidents, near misses and changing conditions.</li>
              <li>Stop work when an immediate or uncontrolled hazard exists.</li>
            </ul>
          </div>

          <div className="rounded-xl border border-amber-200 bg-amber-50 p-5">
            <div className="flex items-center gap-3">
              <TriangleAlert className="h-5 w-5 text-amber-700" aria-hidden="true" />
              <h2 className="font-semibold text-amber-950">Immediate danger</h2>
            </div>
            <p className="mt-3 text-sm leading-6 text-amber-900">
              Stop work, move to a safe location and notify your supervisor. Call 911 for a life-threatening
              emergency.
            </p>
          </div>
        </aside>
      </div>
    </section>
  );
}

function ResourceFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-iron-100 bg-iron-50 px-4 py-3">
      <div className="text-xs font-medium uppercase tracking-wide text-iron-500">{label}</div>
      <div className="mt-1 text-sm font-semibold text-iron-950">{value}</div>
    </div>
  );
}
