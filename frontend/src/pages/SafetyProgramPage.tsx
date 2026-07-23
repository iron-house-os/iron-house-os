import { BookOpenCheck, ExternalLink, HardHat, ShieldCheck } from "lucide-react";

const SAFETY_PROGRAM_URL =
  "https://docs.google.com/document/d/1ApKQs4xIR8axW0lIaeqqATDVaZWs1jvSzaZwYK6wUNw/edit?usp=drivesdk";

const programAreas = [
  "Worker rights, responsibilities and work refusal",
  "Field-level hazard assessment and corrective action",
  "Training, orientation and role-based competency",
  "Excavation, trenching and ground disturbance",
  "Underground and overhead utility controls",
  "Mobile equipment, traffic control and lifting",
  "Confined spaces, fall protection and energy isolation",
  "Silica, asbestos, WHMIS and exposure control",
  "Emergency response, incident investigation and first aid",
  "Injury management, return to work and mental-health support",
];

export function SafetyProgramPage() {
  return (
    <section className="space-y-6">
      <div className="ihos-brand-surface overflow-hidden rounded-xl border border-brand-gold/30 px-6 py-6 text-white shadow-brand">
        <div className="flex items-center gap-4">
          <div className="grid h-14 w-14 place-items-center rounded-xl border border-brand-gold/40 bg-white/10 text-brand-gold">
            <HardHat />
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-gold">Controlled company program</div>
            <h1 className="mt-2 text-3xl font-semibold text-brand-silver">Safety Manual</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-100">
              Iron House Occupational Health, Safety & Environmental Program for civil, earthworks, excavation and utility operations.
            </p>
          </div>
        </div>
      </div>

      <article className="rounded-xl border border-brand-gold/40 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex gap-3">
            <BookOpenCheck className="mt-0.5 h-5 w-5 text-brand-gold-dark" />
            <div>
              <h2 className="font-semibold text-iron-950">Occupational Health, Safety & Environmental Program</h2>
              <p className="mt-1 text-sm text-iron-500">British Columbia · Controlled document · Revision 1.2 · July 23, 2026</p>
            </div>
          </div>
          <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">Current</span>
        </div>

        <p className="mt-4 max-w-4xl text-sm leading-6 text-iron-600">
          Revision 1.2 includes the civil-construction benchmark improvements adopted from the reviewed industry manual: new-worker identification, role-based competency controls, supervisor due-diligence records, task-specific safe job procedures, ground-disturbance controls, emergency action cards, injury management and post-incident support.
        </p>

        <a
          href={SAFETY_PROGRAM_URL}
          target="_blank"
          rel="noreferrer"
          className="mt-5 inline-flex items-center gap-2 rounded-md bg-brand-gold px-4 py-2 text-sm font-semibold text-brand-black"
        >
          Open controlled safety manual
          <ExternalLink className="h-4 w-4" />
        </a>
      </article>

      <section className="rounded-xl border border-iron-100 bg-white p-6 shadow-sm">
        <div className="flex gap-3">
          <ShieldCheck className="mt-0.5 h-5 w-5 text-brand-gold-dark" />
          <div>
            <h2 className="font-semibold text-iron-950">Program coverage</h2>
            <p className="mt-1 text-sm text-iron-500">Use the controlled manual together with project-specific plans, permits, engineered instructions and current legal requirements.</p>
          </div>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          {programAreas.map((area) => (
            <div key={area} className="rounded-md border border-iron-100 bg-iron-50 p-3 text-sm font-medium text-iron-700">
              {area}
            </div>
          ))}
        </div>
      </section>
    </section>
  );
}
