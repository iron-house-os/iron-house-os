import { FormEvent, useState } from "react";

import { useAuth } from "../contexts/AuthContext";

export function PasswordRecoveryPage() {
  const { changePassword, logout, user } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (newPassword !== confirmation) {
      setError("New password confirmation does not match.");
      return;
    }
    setIsSubmitting(true);
    try {
      await changePassword(currentPassword, newPassword);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Password change failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-iron-950 px-4 py-10 text-iron-950">
      <section className="w-full max-w-md rounded-2xl border border-white/10 bg-white p-8 shadow-2xl">
        <div className="text-xs font-semibold uppercase tracking-[0.2em] text-signal-green">
          Account recovery
        </div>
        <h1 className="mt-2 text-2xl font-semibold">Choose a permanent password</h1>
        <p className="mt-2 text-sm text-iron-600">
          {user?.display_name}, an administrator issued a temporary password. Change it before
          opening company workflows.
        </p>
        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <label className="block text-sm font-medium text-iron-800">
            Temporary password
            <input
              type="password"
              autoComplete="current-password"
              required
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              className="mt-2 w-full rounded-lg border border-iron-200 px-3 py-3"
            />
          </label>
          <label className="block text-sm font-medium text-iron-800">
            New password
            <input
              type="password"
              autoComplete="new-password"
              minLength={12}
              required
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              className="mt-2 w-full rounded-lg border border-iron-200 px-3 py-3"
            />
          </label>
          <label className="block text-sm font-medium text-iron-800">
            Confirm new password
            <input
              type="password"
              autoComplete="new-password"
              minLength={12}
              required
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
              className="mt-2 w-full rounded-lg border border-iron-200 px-3 py-3"
            />
          </label>
          {error ? (
            <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
              {error}
            </div>
          ) : null}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-lg bg-iron-950 px-4 py-3 text-sm font-semibold text-white disabled:opacity-60"
          >
            {isSubmitting ? "Changing password…" : "Change password"}
          </button>
          <button
            type="button"
            onClick={() => void logout()}
            className="w-full text-sm font-medium text-iron-600 underline"
          >
            Sign out
          </button>
        </form>
      </section>
    </main>
  );
}
