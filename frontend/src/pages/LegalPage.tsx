import { useEffect, type PropsWithChildren } from "react";
import { Link } from "react-router-dom";
import { Scale, ShieldCheck } from "lucide-react";

type LegalDocument = "privacy" | "terms";

const EFFECTIVE_DATE = "September 24, 2026";
const PRIVACY_PATH = "/legal/privacy";
const TERMS_PATH = "/legal/terms";

function LegalSection({ title, children }: PropsWithChildren<{ title: string }>) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold text-iron-950">{title}</h2>
      <div className="space-y-3 text-sm leading-7 text-iron-700">{children}</div>
    </section>
  );
}

function PrivacyPolicy() {
  return (
    <>
      <LegalSection title="1. Scope and operator">
        <p>
          This Privacy Policy explains how Iron House OS ("IHOS"), operated for Iron House
          Contracting Ltd., handles information when authorised personnel use the IHOS website,
          workforce portals, project tools, and approved integrations.
        </p>
      </LegalSection>

      <LegalSection title="2. Information IHOS handles">
        <p>Depending on the modules assigned to an authorised user, IHOS may handle:</p>
        <ul className="list-disc space-y-2 pl-6">
          <li>account identifiers, contact information, roles, and authentication records;</li>
          <li>project, estimating, supplier, equipment, safety, and operational records;</li>
          <li>documents, photographs, form submissions, and audit evidence;</li>
          <li>
            employee onboarding information, including restricted payroll, tax, banking,
            emergency-contact, certification, and identification fields;
          </li>
          <li>
            security and diagnostic information such as request identifiers, access outcomes,
            timestamps, and privacy-preserving login-throttle records; and
          </li>
          <li>information received through an integration that an administrator enables.</li>
        </ul>
      </LegalSection>

      <LegalSection title="3. QuickBooks Online connection">
        <p>
          A company administrator may choose to connect IHOS to QuickBooks Online through
          Intuit's OAuth authorisation process. The current IHOS integration uses the QuickBooks
          accounting permission only to retrieve and verify the connected company's CompanyInfo.
          IHOS does not create, update, delete, email, import, export, or synchronise accounting
          records through this connection.
        </p>
        <p>
          IHOS stores the selected QuickBooks company identifier, company name, connection status,
          and encrypted OAuth credentials on the server. Access and refresh tokens are not returned
          to browser storage or written to ordinary application logs. An administrator can
          disconnect the company and request provider-token revocation from IHOS.
        </p>
      </LegalSection>

      <LegalSection title="4. Why information is used">
        <p>IHOS uses information to:</p>
        <ul className="list-disc space-y-2 pl-6">
          <li>authenticate users and apply role-based access controls;</li>
          <li>deliver the operational workflows selected by Iron House management;</li>
          <li>protect company, employee, project, and financial information;</li>
          <li>maintain audit, recovery, quality-control, and security evidence; and</li>
          <li>meet applicable contractual, regulatory, and legal obligations.</li>
        </ul>
      </LegalSection>

      <LegalSection title="5. Disclosure and service providers">
        <p>
          IHOS does not sell personal information. Information may be made available to authorised
          Iron House personnel, approved service providers that support IHOS operations, an
          integration provider selected by an administrator, or a regulator or other party when
          disclosure is required by law. Service providers are expected to receive only the access
          needed for their approved function.
        </p>
      </LegalSection>

      <LegalSection title="6. Storage, security, and retention">
        <p>
          IHOS uses administrative, technical, and access controls designed to protect information,
          including HTTPS transport, server-side secret handling, encryption for designated
          restricted fields and integration credentials, role controls, and audit records. No
          system can guarantee absolute security.
        </p>
        <p>
          Records are retained for operational, recovery, audit, contractual, and legal needs.
          Retention varies by record type. QuickBooks connection credentials are retained until the
          connection is removed, revoked, replaced, or otherwise expires, subject to protected
          backup and audit processes.
        </p>
      </LegalSection>

      <LegalSection title="7. Cookies and browser storage">
        <p>
          IHOS uses an essential secure session cookie to maintain authenticated access. It may use
          browser storage for account-bound draft recovery and interface state. IHOS does not use
          advertising cookies in the application.
        </p>
      </LegalSection>

      <LegalSection title="8. Access, correction, and questions">
        <p>
          An authorised user may request access to or correction of information through Iron House
          management, subject to identity verification and any legal or record-preservation
          requirements. Privacy questions and requests can be sent to{
          " "
        }<a className="font-semibold text-brand-gold-dark underline" href="mailto:jeremie@ironhousecontracting.com">
          jeremie@ironhousecontracting.com
        </a>.
        </p>
      </LegalSection>

      <LegalSection title="9. Changes to this policy">
        <p>
          This policy may be updated when IHOS workflows, integrations, or legal requirements
          change. The effective date shown on this page identifies the current published version.
        </p>
      </LegalSection>
    </>
  );
}

function TermsOfUse() {
  return (
    <>
      <LegalSection title="1. Agreement and authorised users">
        <p>
          These End-User Licence Terms govern access to Iron House OS ("IHOS"), operated for Iron
          House Contracting Ltd. By accessing IHOS, you confirm that you are authorised by Iron
          House and agree to follow these terms and the policies, permissions, and approvals that
          apply to your role.
        </p>
      </LegalSection>

      <LegalSection title="2. Internal-use licence">
        <p>
          IHOS grants authorised users a limited, revocable, non-exclusive, non-transferable right
          to use the application for approved Iron House business. No ownership interest is
          transferred. Users may not copy, sell, sublicense, reverse engineer, bypass security, or
          use IHOS for an unauthorised person or purpose.
        </p>
      </LegalSection>

      <LegalSection title="3. Account and acceptable-use responsibilities">
        <ul className="list-disc space-y-2 pl-6">
          <li>Keep sign-in credentials and access links confidential.</li>
          <li>Use only the modules, projects, records, and integrations assigned to your role.</li>
          <li>Enter accurate information and preserve required source evidence.</li>
          <li>Do not upload malicious, unlawful, infringing, or unrelated material.</li>
          <li>Do not attempt to disable audit, approval, security, or record controls.</li>
          <li>Promptly report suspected unauthorised access, loss, or disclosure.</li>
        </ul>
      </LegalSection>

      <LegalSection title="4. QuickBooks Online connection">
        <p>
          Only an authorised administrator may connect or disconnect a QuickBooks Online company.
          Intuit's separate terms and privacy policy also apply to the provider authorisation. The
          current IHOS connection retrieves CompanyInfo solely to verify the selected company. It
          does not create, update, delete, email, import, export, or synchronise invoices, bills,
          customers, vendors, payments, payroll, taxes, journal entries, attachments, or other
          accounting records.
        </p>
      </LegalSection>

      <LegalSection title="5. Company records and confidentiality">
        <p>
          Information entered into IHOS for Iron House business is a company record unless an
          applicable agreement or law provides otherwise. Users must protect confidential,
          employee, client, supplier, project, safety, and financial information and may disclose
          it only for an approved business purpose.
        </p>
      </LegalSection>

      <LegalSection title="6. Third-party services">
        <p>
          IHOS may link to or integrate with third-party services selected by Iron House. Those
          services operate under their own terms, availability, permissions, and privacy practices.
          Iron House may change, suspend, or remove an integration when necessary for security,
          compliance, operations, or provider requirements.
        </p>
      </LegalSection>

      <LegalSection title="7. Availability and professional review">
        <p>
          IHOS supports business workflows but does not replace required management approval,
          professional accounting, legal, engineering, safety, or regulatory review. Drafts,
          calculations, automated suggestions, and exports must be checked by the responsible
          person before they are relied upon. IHOS may be unavailable during maintenance, provider
          outages, security response, or recovery work.
        </p>
      </LegalSection>

      <LegalSection title="8. Suspension and termination">
        <p>
          Iron House may suspend or terminate access when a user's role changes, employment or
          engagement ends, security is at risk, these terms are breached, or access is no longer
          required. Record retention, audit, confidentiality, and other obligations that reasonably
          continue after access ends remain in effect.
        </p>
      </LegalSection>

      <LegalSection title="9. Disclaimer and responsibility">
        <p>
          To the extent permitted by applicable law, IHOS is provided for approved internal
          business use without a guarantee that every function will always be uninterrupted or
          error-free. Users remain responsible for following assigned approval gates and checking
          information before making a safety, contractual, financial, payroll, tax, engineering, or
          legal decision.
        </p>
      </LegalSection>

      <LegalSection title="10. Governing law and contact">
        <p>
          These terms are governed by the laws of British Columbia and the applicable laws of
          Canada. Questions can be sent to{
          " "
        }<a className="font-semibold text-brand-gold-dark underline" href="mailto:jeremie@ironhousecontracting.com">
          jeremie@ironhousecontracting.com
        </a>.
        </p>
      </LegalSection>

      <LegalSection title="11. Changes to these terms">
        <p>
          Iron House may update these terms as IHOS workflows, integrations, or requirements
          change. Continued authorised use after an update is published constitutes acceptance of
          the revised terms, subject to applicable law.
        </p>
      </LegalSection>
    </>
  );
}

export function LegalPage({ document }: { document: LegalDocument }) {
  const isPrivacy = document === "privacy";
  const title = isPrivacy ? "Privacy Policy" : "End-User Licence Terms";
  const Icon = isPrivacy ? ShieldCheck : Scale;

  useEffect(() => {
    const previousTitle = window.document.title;
    window.document.title = `${title} | Iron House OS`;
    return () => {
      window.document.title = previousTitle;
    };
  }, [title]);

  return (
    <main className="min-h-screen bg-iron-50 text-iron-950">
      <header className="ihos-brand-surface ihos-steel-grid border-b border-brand-gold/30 text-white">
        <div className="mx-auto flex max-w-5xl flex-col gap-5 px-5 py-8 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <div className="flex items-center gap-4">
            <img
              src="/os-logo-256.png"
              alt="Iron House Contracting"
              className="h-16 w-16 rounded-xl border border-brand-gold/30 object-cover shadow-lg"
            />
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-brand-gold">
                Iron House Contracting
              </p>
              <p className="mt-1 text-2xl font-semibold text-brand-silver">Iron House OS</p>
            </div>
          </div>
          <Link
            to="/"
            className="w-fit rounded-lg border border-brand-gold/60 px-4 py-2 text-sm font-semibold text-brand-gold transition hover:bg-brand-gold hover:text-brand-black"
          >
            Sign in
          </Link>
        </div>
      </header>

      <article className="mx-auto max-w-5xl px-5 py-10 sm:px-8 sm:py-14">
        <div className="rounded-2xl border border-iron-100 bg-white p-6 shadow-sm sm:p-10">
          <div className="flex items-start gap-4 border-b border-iron-100 pb-7">
            <span className="rounded-xl bg-brand-gold/15 p-3 text-brand-gold-dark">
              <Icon aria-hidden="true" className="h-7 w-7" />
            </span>
            <div>
              <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">{title}</h1>
              <p className="mt-2 text-sm text-iron-500">Effective {EFFECTIVE_DATE}</p>
            </div>
          </div>

          <div className="mt-8 space-y-9">
            {isPrivacy ? <PrivacyPolicy /> : <TermsOfUse />}
          </div>

          <nav aria-label="Legal documents" className="mt-10 flex flex-wrap gap-3 border-t border-iron-100 pt-6">
            <Link
              to={PRIVACY_PATH}
              aria-current={isPrivacy ? "page" : undefined}
              className="rounded-lg border border-iron-200 px-4 py-2 text-sm font-semibold text-iron-800 hover:border-brand-gold"
            >
              Privacy Policy
            </Link>
            <Link
              to={TERMS_PATH}
              aria-current={!isPrivacy ? "page" : undefined}
              className="rounded-lg border border-iron-200 px-4 py-2 text-sm font-semibold text-iron-800 hover:border-brand-gold"
            >
              End-User Licence Terms
            </Link>
          </nav>
        </div>
      </article>
    </main>
  );
}
