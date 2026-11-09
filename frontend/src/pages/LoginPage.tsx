import { FormEvent, useState } from "react";

import { useAuth } from "../contexts/AuthContext";

export function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Sign in failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="ihos-brand-surface ihos-steel-grid grid min-h-screen place-items-center px-4 py-10 text-iron-950">
      <section className="w-full max-w-md overflow-hidden rounded-2xl border border-brand-gold/30 bg-white shadow-brand">
        <div className="relative border-b border-brand-gold/20 bg-brand-black px-8 py-8 text-white">
          <div className="flex items-center gap-4">
            <img src="/os-logo-256.png" alt="Iron House Contracting" className="h-20 w-20 rounded-2xl border border-brand-gold/30 object-cover shadow-lg" />
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.24em] text-brand-gold">Iron House Contracting</div>
              <h1 className="mt-2 text-3xl font-semibold text-brand-silver">Iron House OS</h1>
            </div>
          </div>
          <p className="mt-5 text-sm text-iron-100">Secure access to estimating, tenders, projects, RFQs, suppliers, and operations.</p>
        </div>
        <form className="space-y-5 px-8 py-8" onSubmit={handleSubmit}>
          <label className="block text-sm font-medium text-iron-800">
            Email
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-2 w-full rounded-lg border border-iron-200 px-3 py-3 outline-none transition focus:border-brand-gold focus:ring-2 focus:ring-brand-gold/25"
            />
          </label>
          <label className="block text-sm font-medium text-iron-800">
            Password
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-2 w-full rounded-lg border border-iron-200 px-3 py-3 outline-none transition focus:border-brand-gold focus:ring-2 focus:ring-brand-gold/25"
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
            className="w-full rounded-lg bg-brand-gold px-4 py-3 text-sm font-semibold text-brand-black shadow-md transition hover:bg-[#c99b47] disabled:cursor-wait disabled:opacity-60"
          >
            {isSubmitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
