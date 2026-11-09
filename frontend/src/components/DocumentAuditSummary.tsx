import { DocumentAuditSummary as Summary } from "../api/documentAudit";

type Props = {
  summary: Summary;
};

export function DocumentAuditSummary({ summary }: Props) {
  const actions = Object.entries(summary.by_action).sort((left, right) => right[1] - left[1]);

  return (
    <div className="mt-4 space-y-3">
      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-md border border-iron-100 p-3">
          <div className="text-xs uppercase text-iron-500">Matching events</div>
          <div className="mt-1 text-2xl font-semibold text-iron-950">{summary.total}</div>
        </div>
        <div className="rounded-md border border-iron-100 p-3">
          <div className="text-xs uppercase text-iron-500">Successful</div>
          <div className="mt-1 text-2xl font-semibold text-iron-950">{summary.by_outcome.success ?? 0}</div>
        </div>
        <div className="rounded-md border border-iron-100 p-3">
          <div className="text-xs uppercase text-iron-500">Denied</div>
          <div className="mt-1 text-2xl font-semibold text-iron-950">{summary.by_outcome.denied ?? 0}</div>
        </div>
      </div>

      {actions.length > 0 ? (
        <div className="rounded-md border border-iron-100 p-3">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-iron-500">Activity by action</h3>
          <div className="mt-2 grid gap-2 md:grid-cols-2">
            {actions.map(([action, count]) => (
              <div key={action} className="flex items-center justify-between rounded border border-iron-100 px-3 py-2 text-sm">
                <span className="font-medium text-iron-800">{action}</span>
                <span className="font-mono text-iron-600">{count}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
