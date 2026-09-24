import { Link2, Link2Off, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { QuickBooksStatus, quickBooksApi } from "../api/quickBooks";

export function QuickBooksConnectionCard() {
  const [connection, setConnection] = useState<QuickBooksStatus | null>(null);
  const [disconnectConfirmed, setDisconnectConfirmed] = useState(false);
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [environmentConfirmed, setEnvironmentConfirmed] = useState(false);
  const [removeConfirmed, setRemoveConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    const outcome = new URLSearchParams(window.location.search).get("quickbooks");
    if (outcome === "connected") setNotice("QuickBooks connected and company identity verified.");
    if (outcome === "denied") setError("QuickBooks permission was not granted.");
    if (outcome === "failed") setError("QuickBooks could not be connected. Check the connection settings and try again.");
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
      setNotice("QuickBooks disconnected. Local tokens were cleared.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to disconnect QuickBooks.");
    } finally {
      setBusy(false);
    }
  }

  async function configure(event: React.FormEvent) {
    event.preventDefault();
    if (!environmentConfirmed || !clientId.trim() || !clientSecret.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      setConnection(await quickBooksApi.configure({
        client_id: clientId.trim(),
        client_secret: clientSecret.trim(),
        environment_confirmed: true,
      }));
      setClientId("");
      setClientSecret("");
      setEnvironmentConfirmed(false);
      setNotice("QuickBooks credentials saved securely. The Client Secret is not displayed or stored in this browser.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to save QuickBooks credentials.");
    } finally {
      setClientSecret("");
      setBusy(false);
    }
  }

  async function removeConfiguration() {
    if (!removeConfirmed || busy) return;
    setBusy(true);
    setError(null);
    try {
      setConnection(await quickBooksApi.removeConfiguration());
      setRemoveConfirmed(false);
      setNotice("QuickBooks credentials were removed from IHOS.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to remove QuickBooks credentials.");
    } finally {
      setBusy(false);
    }
  }

  const isLive = connection?.environment === "production";
  const environmentName = isLive ? "live company" : "sandbox company";
  const credentialName = isLive ? "Production" : "Development";
  const shortName = isLive ? "live" : "sandbox";
  const environmentIsApproved = connection?.environment === "sandbox" || connection?.live_read_only_approved;

  return <section className="rounded-md border border-iron-100 bg-white p-5">
    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div>
        <div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4" /><h2 className="font-semibold text-iron-950">QuickBooks Online connection</h2><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${isLive ? "bg-red-100 text-red-900" : "bg-amber-100 text-amber-900"}`}>{isLive ? "Live · IHOS read-only" : "Sandbox only"}</span></div>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">{isLive ? "Administrator-controlled live OAuth connection. IHOS only calls CompanyInfo to verify the selected company; no accounting write controls are implemented. Intuit's accounting permission is broader, so owner approval remains required." : "Administrator-controlled OAuth connection. This stage verifies the selected sandbox company only; it cannot create or change accounting records."}</p>
        {connection?.connected ? <div className="mt-3 text-sm"><div className="font-semibold text-emerald-700">Connected: {connection.company_name}</div><div className="mt-1 text-iron-500">Realm {connection.realm_id} · IHOS company verification only</div></div> : <div className="mt-3 text-sm font-semibold text-iron-700">{isLive && connection && !connection.live_read_only_approved ? "Live connection is awaiting owner-approved production activation." : connection?.configured ? (connection.enabled ? `Ready to connect a ${environmentName}.` : `QuickBooks ${shortName} connection is administratively disabled.`) : "Server credentials are not configured yet."}</div>}
      </div>
      {!connection?.connected ? <button type="button" onClick={() => void connect()} disabled={busy || !connection?.enabled || !connection.configured} className="inline-flex items-center justify-center gap-2 rounded-md bg-brand-gold px-4 py-2 text-sm font-semibold text-brand-black disabled:opacity-50"><Link2 className="h-4 w-4" />{busy ? "Opening Intuit…" : `Connect ${environmentName}`}</button> : null}
    </div>
    {notice ? <div role="status" className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div> : null}
    {error ? <div role="alert" className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
    {connection?.last_error ? <div className="mt-3 text-sm text-amber-800">{connection.last_error}</div> : null}
    {connection && !connection.configured && environmentIsApproved ? <form onSubmit={(event) => void configure(event)} className="mt-4 grid gap-3 border-t border-iron-100 pt-4" autoComplete="off">
      <div className={`rounded-md border p-3 text-sm ${isLive ? "border-red-200 bg-red-50 text-red-900" : "border-amber-200 bg-amber-50 text-amber-900"}`}>{isLive ? <>Use only the <strong>Production</strong> Client ID and Client Secret from Intuit. These credentials can authorize a live company. IHOS currently uses them only for company identity verification, while Intuit's accounting permission is broader.</> : <>Use only the <strong>Development</strong> Client ID and Client Secret from Intuit. These credentials enable sandbox company verification only.</>}</div>
      <label className="grid gap-1 text-sm font-semibold text-iron-700">{credentialName} Client ID<input value={clientId} onChange={(event) => setClientId(event.target.value)} spellCheck={false} autoCapitalize="none" autoCorrect="off" autoComplete="off" className="rounded-md border border-iron-100 px-3 py-2 font-normal" /></label>
      <label className="grid gap-1 text-sm font-semibold text-iron-700">{credentialName} Client Secret<input type="password" value={clientSecret} onChange={(event) => setClientSecret(event.target.value)} spellCheck={false} autoCapitalize="none" autoCorrect="off" autoComplete="off" className="rounded-md border border-iron-100 px-3 py-2 font-normal" /></label>
      <label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={environmentConfirmed} onChange={(event) => setEnvironmentConfirmed(event.target.checked)} className="mt-1" /><span>{isLive ? "I confirm these are Intuit production credentials and authorize IHOS only for live company identity verification." : "I confirm these are Intuit development credentials for the sandbox company, not live QuickBooks credentials."}</span></label>
      <button type="submit" disabled={busy || !environmentConfirmed || !clientId.trim() || !clientSecret.trim()} className="w-fit rounded-md bg-brand-gold px-4 py-2 text-sm font-semibold text-brand-black disabled:opacity-50">{busy ? "Saving securely…" : `Save ${shortName} credentials`}</button>
    </form> : null}
    {connection?.connected ? <div className="mt-4 border-t border-iron-100 pt-4"><label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={disconnectConfirmed} onChange={(event) => setDisconnectConfirmed(event.target.checked)} className="mt-1" /><span>I confirm that I want to disconnect the QuickBooks {environmentName} and clear the stored IHOS tokens.</span></label><button type="button" onClick={() => void disconnect()} disabled={!disconnectConfirmed || busy} className="mt-3 inline-flex items-center gap-2 rounded-md border border-red-200 px-4 py-2 text-sm font-semibold text-red-700 disabled:opacity-50"><Link2Off className="h-4 w-4" />{busy ? "Disconnecting…" : `Disconnect ${shortName}`}</button></div> : null}
    {connection?.database_configured && !connection.connected ? <div className="mt-4 border-t border-iron-100 pt-4"><label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={removeConfirmed} onChange={(event) => setRemoveConfirmed(event.target.checked)} className="mt-1" /><span>I confirm that I want to remove the saved QuickBooks {shortName} credentials from IHOS.</span></label><button type="button" onClick={() => void removeConfiguration()} disabled={!removeConfirmed || busy} className="mt-3 inline-flex items-center gap-2 rounded-md border border-red-200 px-4 py-2 text-sm font-semibold text-red-700 disabled:opacity-50"><Link2Off className="h-4 w-4" />{busy ? "Removing…" : `Remove ${shortName} credentials`}</button></div> : null}
  </section>;
}
