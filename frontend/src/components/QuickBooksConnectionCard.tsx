import { Link2, Link2Off, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { QuickBooksStatus, quickBooksApi } from "../api/quickBooks";

export function QuickBooksConnectionCard() {
  const [connection, setConnection] = useState<QuickBooksStatus | null>(null);
  const [disconnectConfirmed, setDisconnectConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    const outcome = new URLSearchParams(window.location.search).get("quickbooks");
    if (outcome === "connected") setNotice("QuickBooks sandbox connected and company identity verified.");
    if (outcome === "denied") setError("QuickBooks permission was not granted.");
    if (outcome === "failed") setError("QuickBooks could not be connected. Check the sandbox settings and try again.");
    quickBooksApi.status()
      .then(setConnection)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Unable to load QuickBooks status."));
  }, []);

  async function connect() {
    setBusy(true);
    setError(null);
    try {
      const result = await quickBooksApi.startOAuth();
      window.location.assign(result.authorization_url);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to start QuickBooks connection.");
      setBusy(false);
    }
  }

  async function disconnect() {
    if (!disconnectConfirmed || busy) return;
    setBusy(true);
    setError(null);
    try {
      setConnection(await quickBooksApi.disconnect());
      setDisconnectConfirmed(false);
      setNotice("QuickBooks sandbox disconnected. Local tokens were cleared.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to disconnect QuickBooks.");
    } finally {
      setBusy(false);
    }
  }

  return <section className="rounded-md border border-iron-100 bg-white p-5">
    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div>
        <div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4" /><h2 className="font-semibold text-iron-950">QuickBooks Online connection</h2><span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-900">Sandbox only</span></div>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">Administrator-controlled OAuth connection. This stage verifies the selected sandbox company only; it cannot create or change accounting records.</p>
        {connection?.connected ? <div className="mt-3 text-sm"><div className="font-semibold text-emerald-700">Connected: {connection.company_name}</div><div className="mt-1 text-iron-500">Realm {connection.realm_id} · read-only company verification</div></div> : <div className="mt-3 text-sm font-semibold text-iron-700">{connection?.configured ? "Ready to connect a sandbox company." : "Server credentials are not configured yet."}</div>}
      </div>
      {!connection?.connected ? <button type="button" onClick={() => void connect()} disabled={busy || !connection?.enabled || !connection.configured} className="inline-flex items-center justify-center gap-2 rounded-md bg-brand-gold px-4 py-2 text-sm font-semibold text-brand-black disabled:opacity-50"><Link2 className="h-4 w-4" />{busy ? "Opening Intuit…" : "Connect sandbox"}</button> : null}
    </div>
    {notice ? <div role="status" className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div> : null}
    {error ? <div role="alert" className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
    {connection?.last_error ? <div className="mt-3 text-sm text-amber-800">{connection.last_error}</div> : null}
    {connection?.connected ? <div className="mt-4 border-t border-iron-100 pt-4"><label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={disconnectConfirmed} onChange={(event) => setDisconnectConfirmed(event.target.checked)} className="mt-1" /><span>I confirm that I want to disconnect the QuickBooks sandbox company and clear the stored IHOS tokens.</span></label><button type="button" onClick={() => void disconnect()} disabled={!disconnectConfirmed || busy} className="mt-3 inline-flex items-center gap-2 rounded-md border border-red-200 px-4 py-2 text-sm font-semibold text-red-700 disabled:opacity-50"><Link2Off className="h-4 w-4" />{busy ? "Disconnecting…" : "Disconnect sandbox"}</button></div> : null}
  </section>;
}
