import { KeyRound, ShieldCheck } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { RoleAccess, authApi } from "../api/auth";
import { useAuth } from "../contexts/AuthContext";

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
    </section>
  );
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
