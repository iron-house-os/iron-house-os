import { FormEvent, type ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, ChevronRight, LockKeyhole, ShieldCheck } from "lucide-react";
import { useParams } from "react-router-dom";

import {
  employeeOnboardingApi,
  OnboardingRecord,
  PortalCertification,
  PortalPacket,
} from "../api/employeeOnboarding";

const FORM_SECTIONS = [
  ["personal_information", "Personal information"],
  ["address", "Home address"],
  ["emergency_contact", "Emergency contact"],
  ["payroll", "Payroll and direct deposit"],
  ["tax_forms", "2026 TD1 tax forms"],
  ["employment_agreements", "Agreements and policies"],
  ["certifications", "Licences and certifications"],
  ["ppe_requirements", "PPE requirements"],
] as const;

type FormSection = typeof FORM_SECTIONS[number][0];
type FormDrafts = { [Key in FormSection]: NonNullable<PortalPacket[Key]> };

const FEDERAL_TD1_LABELS = [
  "1. Basic personal amount",
  "2. Caregiver amount for infirm children under 18",
  "3. Age amount",
  "4. Pension income amount",
  "5. Tuition",
  "6. Disability amount",
  "7. Spouse or common-law partner amount",
  "8. Eligible dependant amount",
  "9. Caregiver amount for eligible dependant or spouse",
  "10. Caregiver amount for dependants age 18 or older",
  "11. Amounts transferred from spouse or common-law partner",
  "12. Amounts transferred from a dependant",
] as const;

const BC_TD1_LABELS = [
  "1. Basic personal amount",
  "2. Age amount",
  "3. Pension income amount",
  "4. Tuition",
  "5. Disability amount",
  "6. Spouse or common-law partner amount",
  "7. Eligible dependant amount",
  "8. British Columbia caregiver amount",
  "9. Amounts transferred from spouse or common-law partner",
  "10. Amounts transferred from a dependant",
] as const;

export function EmployeeOnboardingPortalPage() {
  const { token = "" } = useParams();
  const [record, setRecord] = useState<OnboardingRecord | null>(null);
  const [packet, setPacket] = useState<PortalPacket | null>(null);
  const [drafts, setDrafts] = useState<FormDrafts | null>(null);
  const [activeSection, setActiveSection] = useState<FormSection | "review">("personal_information");
  const [acknowledged, setAcknowledged] = useState(false);
  const [signatureName, setSignatureName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await employeeOnboardingApi.portalRecord(token);
      setRecord(result.onboarding);
      setPacket(result.packet);
      setDrafts(buildDrafts(result.onboarding, result.packet));
      setSignatureName(result.packet.signature_name ?? "");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Invitation is invalid, revoked, or expired.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  const savedSections = useMemo(
    () => FORM_SECTIONS.filter(([key]) => packet?.[key] !== null).map(([key]) => key),
    [packet],
  );
  const submitted = record ? ["submitted", "approved", "active"].includes(record.status) : false;

  function updateDraft<Key extends FormSection>(key: Key, value: FormDrafts[Key]) {
    setDrafts((current) => current ? { ...current, [key]: value } : current);
  }

  async function saveSection(event: FormEvent) {
    event.preventDefault();
    if (!packet || !drafts || activeSection === "review") return;
    setSaving(true); setError(null); setMessage(null);
    try {
      const candidate = { ...packet, [activeSection]: drafts[activeSection], signature_name: null, signed_at: null };
      const result = await employeeOnboardingApi.savePortalProgress(token, candidate);
      setRecord(result.onboarding); setPacket(result.packet);
      setMessage(`${sectionLabel(activeSection)} saved securely in IHOS.`);
      const index = FORM_SECTIONS.findIndex(([key]) => key === activeSection);
      setActiveSection(index === FORM_SECTIONS.length - 1 ? "review" : FORM_SECTIONS[index + 1][0]);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to save this onboarding form.");
    } finally { setSaving(false); }
  }

  async function submit() {
    if (!packet) return;
    setSaving(true); setError(null); setMessage(null);
    try {
      const result = await employeeOnboardingApi.submitPortal(token, packet, acknowledged, signatureName);
      setRecord(result.onboarding); setPacket(result.packet);
      setMessage("Onboarding submitted for management review. Submission does not activate employment or site deployment.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to submit onboarding.");
    } finally { setSaving(false); }
  }

  return (
    <main className="min-h-screen bg-iron-50 px-4 py-8 text-iron-950 sm:py-12">
      <div className="mx-auto max-w-5xl space-y-6">
        <header className="ihos-brand-surface rounded-xl border border-brand-gold/30 px-6 py-6 text-white shadow-brand">
          <div className="flex items-start gap-4">
            <div className="grid h-12 w-12 place-items-center rounded-xl border border-brand-gold/40 bg-white/10 text-brand-gold"><ShieldCheck /></div>
            <div><div className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-gold">Iron House Contracting</div><h1 className="mt-2 text-3xl font-semibold text-brand-silver">Employee onboarding</h1><p className="mt-2 text-sm leading-6 text-iron-100">Complete and save each assigned form securely inside IHOS.</p></div>
          </div>
        </header>

        {loading ? <Notice role="status">Opening secure invitation…</Notice> : null}
        {error ? <Notice role="alert" tone="error">{error}</Notice> : null}
        {message ? <Notice role="status" tone="success">{message}</Notice> : null}

        {record && packet && drafts ? <>
          <section className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-xl font-semibold">Welcome, {record.preferred_name || record.legal_first_name}</h2><p className="mt-1 text-sm text-iron-500">{labelValue(record.position)} · start date {record.start_date}</p></div><span className="rounded-full bg-iron-100 px-3 py-1.5 text-sm font-semibold">{savedSections.length} of {FORM_SECTIONS.length} forms saved</span></div>
            <div className="mt-4 flex items-start gap-2 rounded-md bg-iron-50 p-3 text-xs leading-5 text-iron-600"><LockKeyhole className="mt-0.5 h-4 w-4 shrink-0" />Personal, banking, SIN, and tax values are encrypted before storage. They are not placed in the invitation email, QR code, admin register, or audit details.</div>
            {record.correction_note ? <p className="mt-4 rounded-md bg-amber-50 p-3 text-sm text-amber-900">Management correction request: {record.correction_note}</p> : null}
          </section>

          {submitted ? <section className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-5 text-emerald-900 shadow-sm"><CheckCircle2 className="mt-0.5 h-5 w-5" /><div><h2 className="font-semibold">Submitted for review</h2><p className="mt-1 text-sm">Management must still approve the record and complete orientation, qualification, and deployment controls before activation.</p></div></section> :
            <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
              <nav aria-label="Onboarding forms" className="h-fit rounded-xl border border-iron-100 bg-white p-3 shadow-sm">
                {FORM_SECTIONS.map(([key, label], index) => <button key={key} type="button" onClick={() => setActiveSection(key)} className={`mb-1 flex min-h-11 w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm ${activeSection === key ? "bg-brand-gold font-semibold text-brand-black" : "text-iron-700 hover:bg-iron-50"}`}><span className={`grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-bold ${savedSections.includes(key) ? "bg-emerald-100 text-emerald-800" : "bg-iron-100"}`}>{savedSections.includes(key) ? "✓" : index + 1}</span><span className="flex-1">{label}</span><ChevronRight className="h-4 w-4" /></button>)}
                <button type="button" onClick={() => setActiveSection("review")} className={`flex min-h-11 w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm ${activeSection === "review" ? "bg-brand-gold font-semibold" : "text-iron-700 hover:bg-iron-50"}`}><span className="grid h-6 w-6 place-items-center rounded-full bg-iron-100 text-xs font-bold">9</span><span className="flex-1">Review and submit</span><ChevronRight className="h-4 w-4" /></button>
              </nav>

              {activeSection === "review" ? <ReviewSection record={record} savedSections={savedSections} acknowledged={acknowledged} signatureName={signatureName} saving={saving} onAcknowledged={setAcknowledged} onSignatureName={setSignatureName} onSection={setActiveSection} onSubmit={() => void submit()} /> :
                <form onSubmit={saveSection} className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm">
                  <SectionHeading title={sectionLabel(activeSection)} saved={savedSections.includes(activeSection)} />
                  <div className="mt-5">
                    {activeSection === "personal_information" ? <PersonalForm record={record} value={drafts.personal_information} onChange={(value) => updateDraft("personal_information", value)} /> : null}
                    {activeSection === "address" ? <AddressForm value={drafts.address} onChange={(value) => updateDraft("address", value)} /> : null}
                    {activeSection === "emergency_contact" ? <EmergencyForm value={drafts.emergency_contact} onChange={(value) => updateDraft("emergency_contact", value)} /> : null}
                    {activeSection === "payroll" ? <PayrollForm value={drafts.payroll} onChange={(value) => updateDraft("payroll", value)} /> : null}
                    {activeSection === "tax_forms" ? <TaxForm value={drafts.tax_forms} onChange={(value) => updateDraft("tax_forms", value)} /> : null}
                    {activeSection === "employment_agreements" ? <AgreementsForm record={record} value={drafts.employment_agreements} onChange={(value) => updateDraft("employment_agreements", value)} /> : null}
                    {activeSection === "certifications" ? <CertificationsForm value={drafts.certifications} onChange={(value) => updateDraft("certifications", value)} /> : null}
                    {activeSection === "ppe_requirements" ? <PPEForm value={drafts.ppe_requirements} onChange={(value) => updateDraft("ppe_requirements", value)} /> : null}
                  </div>
                  <button disabled={saving} className="mt-6 min-h-11 rounded-md bg-brand-gold px-5 py-2 text-sm font-semibold text-brand-black disabled:opacity-50">{saving ? "Saving securely…" : "Save and continue"}</button>
                </form>}
            </div>}
        </> : null}
      </div>
    </main>
  );
}

function PersonalForm({ record, value, onChange }: { record: OnboardingRecord; value: FormDrafts["personal_information"]; onChange: (value: FormDrafts["personal_information"]) => void }) {
  return <div className="grid gap-4 sm:grid-cols-2"><ReadOnly label="Legal name" value={`${record.legal_first_name} ${record.legal_last_name}`} /><ReadOnly label="Invitation email" value={record.personal_email} /><Field label="Preferred name"><input value={value.preferred_name ?? ""} onChange={(event) => onChange({ ...value, preferred_name: event.target.value || null })} /></Field><Field label="Mobile phone"><input required type="tel" value={value.mobile_phone} onChange={(event) => onChange({ ...value, mobile_phone: event.target.value })} /></Field><Field label="Date of birth"><input required type="date" value={value.date_of_birth} onChange={(event) => onChange({ ...value, date_of_birth: event.target.value })} /></Field></div>;
}

function AddressForm({ value, onChange }: { value: FormDrafts["address"]; onChange: (value: FormDrafts["address"]) => void }) {
  return <div className="grid gap-4 sm:grid-cols-2"><Field label="Street address"><input required value={value.street_address} onChange={(event) => onChange({ ...value, street_address: event.target.value })} /></Field><Field label="Unit"><input value={value.unit ?? ""} onChange={(event) => onChange({ ...value, unit: event.target.value || null })} /></Field><Field label="City"><input required value={value.city} onChange={(event) => onChange({ ...value, city: event.target.value })} /></Field><Field label="Province"><input required value={value.province} onChange={(event) => onChange({ ...value, province: event.target.value })} /></Field><Field label="Postal code"><input required placeholder="V1G 1A1" value={value.postal_code} onChange={(event) => onChange({ ...value, postal_code: event.target.value.toUpperCase() })} /></Field><Field label="Country"><input required value={value.country} onChange={(event) => onChange({ ...value, country: event.target.value })} /></Field></div>;
}

function EmergencyForm({ value, onChange }: { value: FormDrafts["emergency_contact"]; onChange: (value: FormDrafts["emergency_contact"]) => void }) {
  return <div className="grid gap-4 sm:grid-cols-2"><Field label="Contact full name"><input required value={value.full_name} onChange={(event) => onChange({ ...value, full_name: event.target.value })} /></Field><Field label="Relationship"><input required value={value.relationship} onChange={(event) => onChange({ ...value, relationship: event.target.value })} /></Field><Field label="Primary phone"><input required type="tel" value={value.primary_phone} onChange={(event) => onChange({ ...value, primary_phone: event.target.value })} /></Field><Field label="Alternate phone"><input type="tel" value={value.alternate_phone ?? ""} onChange={(event) => onChange({ ...value, alternate_phone: event.target.value || null })} /></Field></div>;
}

function PayrollForm({ value, onChange }: { value: FormDrafts["payroll"]; onChange: (value: FormDrafts["payroll"]) => void }) {
  const direct = value.payment_method === "direct_deposit";
  return <div className="space-y-5"><fieldset><legend className="text-sm font-semibold">Payment method</legend><div className="mt-2 flex flex-wrap gap-4"><Radio checked={direct} label="Direct deposit" onChange={() => onChange({ ...value, payment_method: "direct_deposit" })} /><Radio checked={!direct} label="Cheque" onChange={() => onChange({ ...value, payment_method: "cheque", account_holder_name: null, institution_number: null, transit_number: null, account_number: null, direct_deposit_authorized: false })} /></div></fieldset>{direct ? <><div className="grid gap-4 sm:grid-cols-2"><Field label="Account holder name"><input required autoComplete="off" value={value.account_holder_name ?? ""} onChange={(event) => onChange({ ...value, account_holder_name: event.target.value })} /></Field><Field label="Institution number (3 digits)"><input required inputMode="numeric" pattern="[0-9]{3}" autoComplete="off" value={value.institution_number ?? ""} onChange={(event) => onChange({ ...value, institution_number: digits(event.target.value, 3) })} /></Field><Field label="Transit number (5 digits)"><input required inputMode="numeric" pattern="[0-9]{5}" autoComplete="off" value={value.transit_number ?? ""} onChange={(event) => onChange({ ...value, transit_number: digits(event.target.value, 5) })} /></Field><Field label="Account number"><input required type="password" inputMode="numeric" pattern="[0-9]{5,17}" autoComplete="off" value={value.account_number ?? ""} onChange={(event) => onChange({ ...value, account_number: digits(event.target.value, 17) })} /></Field></div><Check required checked={value.direct_deposit_authorized} label="I authorise Iron House Contracting to deposit payroll payments to this account." onChange={(checked) => onChange({ ...value, direct_deposit_authorized: checked })} /></> : <p className="rounded-md bg-amber-50 p-3 text-sm text-amber-900">Payroll will issue payment by the approved cheque process until this form is updated.</p>}</div>;
}

function TaxForm({ value, onChange }: { value: FormDrafts["tax_forms"]; onChange: (value: FormDrafts["tax_forms"]) => void }) {
  const isNonResident = value.country_of_permanent_residence.trim().toLocaleLowerCase() !== "canada";
  function updateCountry(country: string) {
    onChange({
      ...value,
      country_of_permanent_residence: country,
      non_resident_world_income_90_percent_or_more:
        country.trim().toLocaleLowerCase() === "canada"
          ? null
          : value.non_resident_world_income_90_percent_or_more,
    });
  }
  function updateWorldIncomeAnswer(answer: boolean) {
    onChange({
      ...value,
      non_resident_world_income_90_percent_or_more: answer,
      federal_claim_amounts: answer ? value.federal_claim_amounts : Array(12).fill("0"),
    });
  }
  return <div className="space-y-6"><p className="rounded-md bg-amber-50 p-3 text-sm leading-6 text-amber-900">Protected B when completed. Enter the values that apply to you. IHOS records the 2026 federal TD1 and British Columbia TD1BC fields; obtain tax advice if you are unsure.</p><div className="grid gap-4 sm:grid-cols-2"><Field label="Social Insurance Number"><input required type="password" inputMode="numeric" pattern="[0-9]{9}" autoComplete="off" value={value.social_insurance_number} onChange={(event) => onChange({ ...value, social_insurance_number: digits(event.target.value, 9) })} /></Field><Field label="Country of permanent residence"><input required value={value.country_of_permanent_residence} onChange={(event) => updateCountry(event.target.value)} /></Field></div>{isNonResident ? <fieldset className="rounded-lg border border-iron-100 p-4"><legend className="px-2 text-sm font-semibold">For non-residents only</legend><p className="text-sm leading-6 text-iron-700">Will 90% or more of your world income be included in determining your taxable income earned in Canada in 2026?</p><div className="mt-3 flex flex-wrap gap-4"><Radio name="non-resident-world-income" required checked={value.non_resident_world_income_90_percent_or_more === true} label="Yes" onChange={() => updateWorldIncomeAnswer(true)} /><Radio name="non-resident-world-income" required checked={value.non_resident_world_income_90_percent_or_more === false} label="No" onChange={() => updateWorldIncomeAnswer(false)} /></div>{value.non_resident_world_income_90_percent_or_more === false ? <p className="mt-3 rounded-md bg-amber-50 p-3 text-sm text-amber-900">The 2026 federal TD1 requires a zero total claim when the answer is no. IHOS has set all federal claim lines to zero.</p> : null}</fieldset> : null}<TaxCredits title="Federal TD1 — 2026" labels={FEDERAL_TD1_LABELS} amounts={value.federal_claim_amounts} onChange={(amounts) => onChange({ ...value, federal_claim_amounts: amounts })} /><div className="grid gap-3"><Check checked={value.federal_more_than_one_employer} label="I have more than one employer or payer and already claimed credits on another 2026 TD1." onChange={(checked) => onChange({ ...value, federal_more_than_one_employer: checked })} /><Check checked={value.federal_total_income_less_than_claim} label="My total income will be less than my federal total claim amount." onChange={(checked) => onChange({ ...value, federal_total_income_less_than_claim: checked })} /><Field label="Additional tax to deduct from each payment"><input required type="number" min="0" step="0.01" value={value.additional_tax_per_payment} onChange={(event) => onChange({ ...value, additional_tax_per_payment: event.target.value })} /></Field><Check required checked={value.federal_certified} label="I certify that my 2026 federal TD1 information is correct and complete." onChange={(checked) => onChange({ ...value, federal_certified: checked })} /></div><TaxCredits title="British Columbia TD1BC — 2026" labels={BC_TD1_LABELS} amounts={value.bc_claim_amounts} onChange={(amounts) => onChange({ ...value, bc_claim_amounts: amounts })} /><div className="grid gap-3"><Check checked={value.bc_more_than_one_employer} label="I have more than one employer or payer and already claimed credits on another 2026 TD1BC." onChange={(checked) => onChange({ ...value, bc_more_than_one_employer: checked })} /><Check checked={value.bc_total_income_less_than_claim} label="My total income will be less than my British Columbia total claim amount." onChange={(checked) => onChange({ ...value, bc_total_income_less_than_claim: checked })} /><Check required checked={value.bc_certified} label="I certify that my 2026 British Columbia TD1BC information is correct and complete." onChange={(checked) => onChange({ ...value, bc_certified: checked })} /></div></div>;
}

function TaxCredits({ title, labels, amounts, onChange }: { title: string; labels: readonly string[]; amounts: string[]; onChange: (amounts: string[]) => void }) {
  const total = amounts.reduce((sum, amount) => sum + (Number(amount) || 0), 0);
  return <fieldset className="rounded-lg border border-iron-100 p-4"><legend className="px-2 font-semibold">{title}</legend><div className="grid gap-3 sm:grid-cols-2">{labels.map((label, index) => <Field key={label} label={label}><input required type="number" min="0" step="0.01" value={amounts[index] ?? "0"} onChange={(event) => { const next = [...amounts]; next[index] = event.target.value; onChange(next); }} /></Field>)}</div><p className="mt-4 text-sm font-semibold">Total claim amount: {total.toLocaleString("en-CA", { style: "currency", currency: "CAD" })}</p></fieldset>;
}

function AgreementsForm({ record, value, onChange }: { record: OnboardingRecord; value: FormDrafts["employment_agreements"]; onChange: (value: FormDrafts["employment_agreements"]) => void }) {
  return <div className="space-y-4"><div className="rounded-md bg-iron-50 p-4 text-sm leading-6"><b>Employment record:</b> {labelValue(record.position)}, {labelValue(record.employment_type)}, starting {record.start_date}{record.primary_location ? ` at ${record.primary_location}` : ""}.</div><Check required checked={value.employment_terms_reviewed} label="I reviewed the employment details and terms assigned to this onboarding record." onChange={(checked) => onChange({ ...value, employment_terms_reviewed: checked })} /><Check required checked={value.company_policies_reviewed} label="I reviewed the assigned Iron House company policies and understand how to ask questions." onChange={(checked) => onChange({ ...value, company_policies_reviewed: checked })} /><Check required checked={value.privacy_notice_reviewed} label="I understand that restricted onboarding information is collected for employment, payroll, tax, safety, and access administration." onChange={(checked) => onChange({ ...value, privacy_notice_reviewed: checked })} /><Check required checked={value.purchase_receipt_standard_reviewed} label="I understand the purchase rule: request an IHOS PO, make the purchase, put the PO number on the receipt or invoice, and submit the receipt to Dext." onChange={(checked) => onChange({ ...value, purchase_receipt_standard_reviewed: checked })} /><Check required checked={value.questions_resolved} label="My questions have been answered, or I know who to contact before accepting employment terms or assigned policies." onChange={(checked) => onChange({ ...value, questions_resolved: checked })} /><p className="text-xs leading-5 text-iron-500">This acknowledgement does not replace supervisor-led safety orientation, competency assessment, qualification verification, or site-specific instruction.</p></div>;
}

function CertificationsForm({ value, onChange }: { value: FormDrafts["certifications"]; onChange: (value: FormDrafts["certifications"]) => void }) {
  function update(index: number, updateValue: Partial<PortalCertification>) { const next = [...value.certifications]; next[index] = { ...next[index], ...updateValue }; onChange({ ...value, certifications: next }); }
  return <div className="space-y-4"><Check checked={value.none_to_report} label="I have no licences, tickets, or certifications to report." onChange={(checked) => onChange({ none_to_report: checked, certifications: checked ? [] : value.certifications })} />{!value.none_to_report ? <>{value.certifications.map((item, index) => <div key={index} className="rounded-lg border border-iron-100 p-4"><div className="grid gap-4 sm:grid-cols-2"><Field label="Certification or ticket"><input required value={item.name} onChange={(event) => update(index, { name: event.target.value })} /></Field><Field label="Certificate number"><input value={item.certificate_number ?? ""} onChange={(event) => update(index, { certificate_number: event.target.value || null })} /></Field><Field label="Issuer"><input value={item.issuer ?? ""} onChange={(event) => update(index, { issuer: event.target.value || null })} /></Field><Field label="Expiry date"><input type="date" value={item.expiry_date ?? ""} onChange={(event) => update(index, { expiry_date: event.target.value || null })} /></Field></div><button type="button" className="mt-3 text-sm font-semibold text-red-700" onClick={() => onChange({ ...value, certifications: value.certifications.filter((_, itemIndex) => itemIndex !== index) })}>Remove</button></div>)}<button type="button" className="min-h-11 rounded-md border border-brand-gold/50 px-4 text-sm font-semibold" onClick={() => onChange({ ...value, certifications: [...value.certifications, { name: "", certificate_number: null, issuer: null, expiry_date: null }] })}>Add certification</button>{!value.certifications.length ? <p className="text-sm text-amber-800">Add at least one certification or confirm there are none to report.</p> : null}</> : null}</div>;
}

function PPEForm({ value, onChange }: { value: FormDrafts["ppe_requirements"]; onChange: (value: FormDrafts["ppe_requirements"]) => void }) {
  return <div className="space-y-5"><fieldset><legend className="text-sm font-semibold">Will this position require site PPE?</legend><div className="mt-2 flex gap-4"><Radio checked={value.site_ppe_required} label="Yes" onChange={() => onChange({ ...value, site_ppe_required: true })} /><Radio checked={!value.site_ppe_required} label="No / office only" onChange={() => onChange({ ...value, site_ppe_required: false, boot_size: null, glove_size: null, shirt_size: null, trouser_size: null })} /></div></fieldset>{value.site_ppe_required ? <div className="grid gap-4 sm:grid-cols-2"><Field label="Work boot size"><input required value={value.boot_size ?? ""} onChange={(event) => onChange({ ...value, boot_size: event.target.value })} /></Field><Field label="Glove size"><input required value={value.glove_size ?? ""} onChange={(event) => onChange({ ...value, glove_size: event.target.value })} /></Field><Field label="Shirt / high-visibility size"><input required value={value.shirt_size ?? ""} onChange={(event) => onChange({ ...value, shirt_size: event.target.value })} /></Field><Field label="Trouser size"><input required value={value.trouser_size ?? ""} onChange={(event) => onChange({ ...value, trouser_size: event.target.value })} /></Field></div> : null}<Check checked={value.prescription_safety_glasses} label="I require prescription safety-glasses accommodation." onChange={(checked) => onChange({ ...value, prescription_safety_glasses: checked })} /><Check checked={value.respirator_fit_test_required} label="I may require respirator fit testing." onChange={(checked) => onChange({ ...value, respirator_fit_test_required: checked })} /><Field label="PPE notes or accommodation request"><textarea rows={4} value={value.notes ?? ""} onChange={(event) => onChange({ ...value, notes: event.target.value || null })} /></Field><p className="text-xs leading-5 text-iron-500">Management must verify PPE and any required fit testing before deployment. This form is a sizing and needs record, not proof of issue or competency.</p></div>;
}

function ReviewSection({ record, savedSections, acknowledged, signatureName, saving, onAcknowledged, onSignatureName, onSection, onSubmit }: { record: OnboardingRecord; savedSections: FormSection[]; acknowledged: boolean; signatureName: string; saving: boolean; onAcknowledged: (value: boolean) => void; onSignatureName: (value: string) => void; onSection: (value: FormSection) => void; onSubmit: () => void }) {
  const complete = savedSections.length === FORM_SECTIONS.length;
  return <section className="rounded-xl border border-iron-100 bg-white p-5 shadow-sm"><SectionHeading title="Review and submit" saved={false} /><p className="mt-2 text-sm text-iron-600">Confirm every employee-completed form is saved. Safety orientation, qualification verification, management approval, and portal activation remain separate IHOS controls.</p><div className="mt-5 grid gap-2">{FORM_SECTIONS.map(([key, label]) => <button key={key} type="button" onClick={() => onSection(key)} className="flex min-h-11 items-center justify-between rounded-md border border-iron-100 px-3 text-left text-sm"><span>{label}</span><span className={savedSections.includes(key) ? "font-semibold text-emerald-700" : "font-semibold text-red-700"}>{savedSections.includes(key) ? "Saved" : "Required"}</span></button>)}</div><div className="mt-5 rounded-md bg-iron-50 p-4"><Check required checked={acknowledged} label="I certify that the information I provided is correct and complete to the best of my knowledge, and I understand that submitting sends this onboarding packet to Iron House management for review." onChange={onAcknowledged} /><Field label="Electronic signature — type your full legal name"><input required value={signatureName} onChange={(event) => onSignatureName(event.target.value)} placeholder={`${record.legal_first_name} ${record.legal_last_name}`} /></Field></div><button type="button" disabled={saving || !complete || !acknowledged || !signatureName.trim()} onClick={onSubmit} className="mt-5 min-h-11 rounded-md bg-brand-gold px-5 py-2 text-sm font-semibold text-brand-black disabled:opacity-50">{saving ? "Submitting securely…" : "Submit for management review"}</button></section>;
}

function buildDrafts(record: OnboardingRecord, packet: PortalPacket): FormDrafts {
  return {
    personal_information: packet.personal_information ?? { preferred_name: record.preferred_name, mobile_phone: record.mobile_phone ?? "", date_of_birth: "" },
    address: packet.address ?? { street_address: "", unit: null, city: "", province: "BC", postal_code: "", country: "Canada" },
    emergency_contact: packet.emergency_contact ?? { full_name: "", relationship: "", primary_phone: "", alternate_phone: null },
    payroll: packet.payroll ?? { payment_method: "direct_deposit", account_holder_name: `${record.legal_first_name} ${record.legal_last_name}`, institution_number: null, transit_number: null, account_number: null, direct_deposit_authorized: false },
    tax_forms: packet.tax_forms ?? { form_year: 2026, social_insurance_number: "", country_of_permanent_residence: "Canada", federal_claim_amounts: ["16452", ...Array(11).fill("0")], bc_claim_amounts: ["13216", ...Array(9).fill("0")], federal_more_than_one_employer: false, federal_total_income_less_than_claim: false, non_resident_world_income_90_percent_or_more: null, additional_tax_per_payment: "0", bc_more_than_one_employer: false, bc_total_income_less_than_claim: false, federal_certified: false, bc_certified: false },
    employment_agreements: packet.employment_agreements ?? { employment_terms_reviewed: false, company_policies_reviewed: false, privacy_notice_reviewed: false, purchase_receipt_standard_reviewed: false, questions_resolved: false },
    certifications: packet.certifications ?? { none_to_report: false, certifications: [] },
    ppe_requirements: packet.ppe_requirements ?? { site_ppe_required: record.category === "field_staff", boot_size: null, glove_size: null, shirt_size: null, trouser_size: null, prescription_safety_glasses: false, respirator_fit_test_required: false, notes: null },
  };
}

function sectionLabel(section: FormSection) { return FORM_SECTIONS.find(([key]) => key === section)?.[1] ?? section; }
function digits(value: string, maximum: number) { return value.replace(/\D/g, "").slice(0, maximum); }
function labelValue(value: string) { return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()); }
function Field({ label, children }: { label: string; children: ReactNode }) { return <label className="grid gap-1 text-sm font-medium text-iron-700 [&>input]:min-h-11 [&>input]:rounded-md [&>input]:border [&>input]:px-3 [&>textarea]:rounded-md [&>textarea]:border [&>textarea]:px-3 [&>textarea]:py-2">{label}{children}</label>; }
function ReadOnly({ label, value }: { label: string; value: string }) { return <div><div className="text-sm font-medium text-iron-700">{label}</div><div className="mt-1 min-h-11 rounded-md bg-iron-50 px-3 py-3 text-sm text-iron-700">{value}</div></div>; }
function Check({ label, checked, onChange, required = false }: { label: string; checked: boolean; onChange: (checked: boolean) => void; required?: boolean }) { return <label className="flex items-start gap-3 rounded-md border border-iron-100 p-3 text-sm leading-6"><input required={required} className="mt-1 h-4 w-4" type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} /><span>{label}</span></label>; }
function Radio({ label, checked, onChange, name, required = false }: { label: string; checked: boolean; onChange: () => void; name?: string; required?: boolean }) { return <label className="flex min-h-11 items-center gap-2 rounded-md border border-iron-100 px-3 text-sm"><input type="radio" name={name} required={required} checked={checked} onChange={onChange} />{label}</label>; }
function Notice({ role, tone, children }: { role: "alert" | "status"; tone?: "error" | "success"; children: ReactNode }) { const style = tone === "error" ? "border-red-200 bg-red-50 text-red-700" : tone === "success" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-iron-100 bg-white text-iron-700"; return <div role={role} className={`rounded-md border p-4 text-sm ${style}`}>{children}</div>; }
function SectionHeading({ title, saved }: { title: string; saved: boolean }) { return <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-xl font-semibold">{title}</h2>{saved ? <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-800">Saved</span> : null}</div>; }
