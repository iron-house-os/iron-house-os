import { BookOpenCheck, ShieldAlert, Truck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { Equipment, equipmentApi } from "../api/equipment";
import { SAFETY_PROGRAM_URL, safetyProcedures } from "../safetyProcedures";

export function EquipmentFieldPage() {
  const { equipmentId = "" } = useParams();
  const [item, setItem] = useState<Equipment | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    equipmentApi.get(equipmentId)
      .then((value) => { if (active) setItem(value); })
      .catch((current) => { if (active) setError(current instanceof Error ? current.message : "Unable to load equipment field record."); });
    return () => { active = false; };
  }, [equipmentId]);

  const assigned = useMemo(
    () => safetyProcedures.filter((procedure) => (item?.safety_procedure_codes ?? []).includes(procedure.code)),
    [item],
  );

  if (error) return <main className="mx-auto max-w-3xl p-6"><div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{error}</div></main>;
  if (!item) return <main className="grid min-h-[50vh] place-items-center text-sm text-iron-500">Loading equipment field record…</main>;

  return <main className="mx-auto max-w-3xl space-y-5 p-4 sm:p-6">
    <header className="ihos-brand-surface rounded-xl border border-brand-gold/30 p-6 text-white shadow-brand">
      <div className="flex items-start gap-4"><div className="rounded-lg border border-brand-gold/40 bg-white/10 p-3 text-brand-gold"><Truck /></div><div><div className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-gold">Equipment field record</div><h1 className="mt-2 text-2xl font-semibold text-brand-silver">{item.name}</h1><p className="mt-2 text-sm text-iron-100">{item.equipment_type || "Unclassified"} · {item.identifier || "No identifier"}</p></div></div>
    </header>
    <section className="rounded-xl border bg-white p-5">
      <h2 className="font-semibold text-iron-950">Management-assigned safety procedures</h2>
      <p className="mt-2 text-sm leading-6 text-iron-600">These references support field access. They do not replace the supervisor’s task, hazard, competency, permit, or current-condition verification.</p>
      {assigned.length ? <div className="mt-4 grid gap-3">{assigned.map((procedure) => <a key={procedure.code} href={SAFETY_PROGRAM_URL} target="_blank" rel="noreferrer" className="flex min-h-14 items-center gap-3 rounded-lg border border-brand-gold/30 p-4"><BookOpenCheck className="h-5 w-5 shrink-0 text-brand-gold-dark" /><span><b>{procedure.code} · {procedure.title}</b><span className="mt-1 block text-xs text-iron-500">{procedure.category} · Open the current controlled safety program</span></span></a>)}</div> : <div role="alert" className="mt-4 flex gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"><ShieldAlert className="h-5 w-5 shrink-0" /><span>No controlled procedure references are assigned to this equipment record. Contact the responsible supervisor before work.</span></div>}
    </section>
    <p className="text-xs leading-5 text-iron-500">Sign-in remains required. Confirm the equipment identifier before relying on this field record. Printed or downloaded copies of the safety program may be uncontrolled.</p>
  </main>;
}
