import { AlertTriangle, Bot, KeyRound, ShieldCheck, Users } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { IdentityGovernance, RoleAccess, authApi } from "../api/auth";
import { useAuth } from "../contexts/AuthContext";
import { Link } from "react-router-dom";

export function SettingsPage() {
  const { user } = useAuth();
  const [permissions, setPermissions] = useState<RoleAccess | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    authApi.permissions().then(setPermissions).catch((currentError) => {
      setError(currentError instanceof Error ? currentError.message : "Unable to load access settings");
    });
  }, []);

  return (
    <section className="space-y-6">
      <div className="border-b border-iron-100 pb-6">
        <h1 className="text-3xl font-semibold text-iron-950">Settings</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">Account security, access level, and module permissions for the signed-in user.</p>
      </div>

      {error ? <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}

      <div className="grid gap-6 xl:grid-cols-2">
        {user?.role === "admin" || user?.role === "operations_manager" ? (
          <Link to="/iron-house-chat" className="rounded-md border border-brand-gold/40 bg-white p-5 transition hover:bg-brand-gold/10 xl:col-span-2">
            <div className="flex items-center gap-2"><Bot className="h-5 w-5 text-brand-gold" /><h2 className="font-semibold">Iron House Chat</h2></div>
            <p className="mt-2 text-sm text-iron-500">Open the separate, management-only typed AI help assistant with read-only controls.</p>
          </Link>
        ) : null}
        <div className="rounded-md border border-iron-100 bg-white p-5">
          <div className="flex items-center gap-2"><ShieldCheck className="h-5 w-5" /><h2 className="font-semibold">Account and access</h2></div>
          <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
            <Setting label="Name" value={user?.display_name ?? "—"} />
            <Setting label="Email" value={user?.email ?? "—"} />
            <Setting label="Role" value={(user?.role ?? "—").replace("_", " ")} />
            <Setting label="Account" value={user?.is_active ? "Active" : "Inactive"} />
          </dl>
          {permissions ? (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-iron-950">Module permissions</h3>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {Object.entries(permissions.modules).map(([module, actions]) => (
                  <div key={module} className="rounded-md bg-iron-50 p-3 text-sm"><div className="font-medium capitalize">{module.replaceAll("-", " ")}</div><div className="mt-1 text-xs text-iron-500">{actions.join(", ") || "No access"}</div></div>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        <ChangePasswordPanel />
      </div>
      {user?.role === "admin" ? <IdentityGovernancePanel /> : null}
    </section>
  );
}

function IdentityGovernancePanel() {
  const [governance, setGovernance] = useState<IdentityGovernance | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    authApi.identityGovernance().then(setGovernance).catch((currentError) => {
      setError(currentError instanceof Error ? currentError.message : "Unable to load identity governance");
    });
  }, []);

  return (
    <div className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex items-center gap-2"><Users className="h-5 w-5" /><h2 className="font-semibold">Identity Governance Centre</h2></div>
      <p className="mt-2 text-sm text-iron-500">Administrator-only review of company identities, access continuity, and account hygiene.</p>
      {error ? <div role="alert" className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
      {!governance && !error ? <p className="mt-4 text-sm text-iron-500">Loading identity governance…</p> : null}
      {governance ? (
        <>
          <div className="mt-5 grid gap-3 sm:grid-cols-3 xl:grid-cols-6">
            <Metric label="Accounts" value={governance.summary.total_accounts} />
            <Metric label="Active" value={governance.summary.active_accounts} />
            <Metric label="Administrators" value={governance.summary.active_administrators} />
            <Metric label="Legacy domain" value={governance.summary.legacy_domain_accounts} />
            <Metric label="Needs review" value={governance.summary.accounts_requiring_review} />
            <Metric label="Critical" value={governance.summary.critical_findings} />
          </div>
          <div className="mt-6 grid gap-3">
            {governance.findings.length ? governance.findings.map((finding) => (
              <div key={finding.code} className="rounded-md border border-iron-100 p-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className={`mt-0.5 h-5 w-5 ${finding.severity === "critical" ? "text-red-600" : "text-brand-gold"}`} />
                  <div><div className="font-semibold text-iron-950">{finding.title}</div><div className="mt-1 text-sm text-iron-500">{finding.recommendation}</div><div className="mt-2 text-xs uppercase tracking-wide text-iron-500">{finding.severity} · {finding.account_ids.length} affected</div></div>
                </div>
              </div>
            )) : <div className="rounded-md bg-green-50 p-4 text-sm text-green-800">No identity governance findings require action.</div>}
          </div>
          <div className="mt-6 overflow-x-auto" tabIndex={0} aria-label="Identity governance account review table">
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b border-iron-100 text-xs uppercase tracking-wide text-iron-500"><th className="px-3 py-2">Account</th><th className="px-3 py-2">Role</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Review</th></tr></thead>
              <tbody>{governance.accounts.map((account) => <tr key={account.id} className="border-b border-iron-100"><td className="px-3 py-3"><div className="font-medium">{account.display_name}</div><div className="text-xs text-iron-500">{account.email}</div></td><td className="px-3 py-3 capitalize">{account.role.replace("_", " ")}</td><td className="px-3 py-3">{account.is_active ? "Active" : "Inactive"}</td><td className="px-3 py-3 text-iron-500">{account.review_reasons.join(", ") || "Clear"}</td></tr>)}</tbody>
            </table>
          </div>
        </>
      ) : null}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-md bg-iron-50 p-3"><div className="text-xs uppercase tracking-wide text-iron-500">{label}</div><div className="mt-1 text-2xl font-semibold text-iron-950">{value}</div></div>;
}

function ChangePasswordPanel() {
  const { changePassword } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    if (newPassword !== confirmation) {
      setMessage("New password and confirmation do not match.");
      return;
    }
    setIsSaving(true);
    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmation("");
      setMessage("Password updated successfully.");
    } catch (currentError) {
      setMessage(currentError instanceof Error ? currentError.message : "Unable to update password");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="rounded-md border border-iron-100 bg-white p-5">
      <div className="flex items-center gap-2"><KeyRound className="h-5 w-5" /><h2 className="font-semibold">Change password</h2></div>
      <p className="mt-2 text-sm text-iron-500">Use at least 12 characters. Changing it keeps the current secure session active.</p>
      <div className="mt-5 grid gap-4">
        <PasswordInput label="Current password" value={currentPassword} onChange={setCurrentPassword} />
        <PasswordInput label="New password" value={newPassword} onChange={setNewPassword} minLength={12} />
        <PasswordInput label="Confirm new password" value={confirmation} onChange={setConfirmation} minLength={12} />
      </div>
      {message ? <div role="status" className="mt-4 rounded-md bg-iron-50 p-3 text-sm text-iron-700">{message}</div> : null}
      <button disabled={isSaving} type="submit" className="mt-4 rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white disabled:bg-iron-300">{isSaving ? "Updating…" : "Update password"}</button>
    </form>
  );
}

function PasswordInput({ label, value, onChange, minLength }: { label: string; value: string; onChange: (value: string) => void; minLength?: number }) {
  return <label className="grid gap-1 text-sm"><span className="font-medium text-iron-700">{label}</span><input required minLength={minLength} type="password" autoComplete="off" value={value} onChange={(event) => onChange(event.target.value)} className="rounded-md border border-iron-100 px-3 py-2" /></label>;
}

function Setting({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md bg-iron-50 p-3"><dt className="text-xs uppercase tracking-wide text-iron-500">{label}</dt><dd className="mt-1 font-semibold capitalize text-iron-950">{value}</dd></div>;
}
