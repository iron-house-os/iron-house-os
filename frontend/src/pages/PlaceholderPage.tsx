import type { AppModule } from "../modules";

type PlaceholderPageProps = {
  module: AppModule;
};

const readinessItems = [
  "Navigation and route registered",
  "API boundary reserved",
  "Database model mapped where applicable",
  "Business logic intentionally deferred",
];

export function PlaceholderPage({ module }: PlaceholderPageProps) {
  const Icon = module.icon;

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-iron-100 pb-6 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-md bg-iron-950 text-white">
            <Icon className="h-5 w-5" />
          </div>
          <h1 className="text-3xl font-semibold text-iron-950">{module.label}</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-iron-500">{module.description}</p>
        </div>
        <div className="rounded-md border border-iron-100 bg-white px-4 py-3 text-sm">
          <div className="text-xs uppercase tracking-wide text-iron-500">Status</div>
          <div className="font-semibold text-iron-950">{module.status}</div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {readinessItems.map((item) => (
          <div key={item} className="rounded-md border border-iron-100 bg-white p-4">
            <div className="text-sm font-medium text-iron-950">{item}</div>
            <div className="mt-2 h-2 rounded-full bg-iron-100">
              <div className="h-2 w-2/3 rounded-full bg-signal-blue" />
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-md border border-iron-100 bg-white p-5">
        <h2 className="text-base font-semibold text-iron-950">Phase 2 expansion point</h2>
        <p className="mt-2 text-sm leading-6 text-iron-500">
          This screen is ready for workflow components, data tables, filters, uploads, audit trails,
          and AI-assisted actions once the domain rules are introduced.
        </p>
      </div>
    </section>
  );
}
