import { Bot, Brain, Send, ShieldCheck, Upload, Volume2 } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";

import { ChatMessage, ChatStatus, ironHouseChatApi } from "../api/ironHouseChat";
import { useAuth } from "../contexts/AuthContext";
import { useHandsFreeVoice } from "../contexts/HandsFreeVoiceContext";

export function IronHouseChatPage() {
  const { user } = useAuth();
  const [status, setStatus] = useState<ChatStatus | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string>();
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const { speakAssistantResponse } = useHandsFreeVoice();

  useEffect(() => {
    ironHouseChatApi.status().then(setStatus).catch((reason) => setError(reason instanceof Error ? reason.message : "Unable to load Iron House Chat"));
  }, []);

  async function send(text: string) {
    const clean = text.trim();
    if (!clean || sending) return;
    setSending(true); setError(null); setDraft("");
    try {
      const reply = await ironHouseChatApi.send(clean, conversationId);
      setConversationId(reply.conversation.id);
      setMessages((current) => [...current, reply.user_message, reply.assistant_message]);
      if (reply.assistant_message.status === "completed") speakAssistantResponse(reply.assistant_message.content);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to send message");
    } finally { setSending(false); }
  }

  async function importHistory(file: File | undefined) {
    if (!file) return;
    setImporting(true); setImportMessage(null); setError(null);
    try {
      const result = await ironHouseChatApi.importChatGpt(file);
      setImportMessage(`Project Brain updated: ${result.imported} conversations imported, ${result.updated} refreshed, ${result.skipped} unrelated conversations skipped.`);
      setStatus((current) => current ? { ...current, memory_count: result.total_project_memories } : current);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to import ChatGPT history");
    } finally { setImporting(false); }
  }

  if (user?.role !== "admin" && user?.role !== "operations_manager") return <Navigate to="/dashboard" replace />;

  return (
    <section className="space-y-6">
      <div className="border-b border-iron-100 pb-6">
        <div className="flex items-center gap-3"><Bot className="h-8 w-8 text-brand-gold" /><h1 className="text-3xl font-semibold text-iron-950">Iron House Chat</h1></div>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">Management-only OS help. This assistant is separate from ChatGPT and currently operates in read-only mode.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatusCard label="AI service" value={status?.configured ? "Connected" : "Credential required"} />
        <StatusCard label="Project Brain" value={`${status?.memory_count ?? 0} sources`} />
        <StatusCard label="Voice phrase" value='“Hey Chat…”' />
      </div>

      {!status?.configured && status ? <div className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900"><strong>Installation complete; activation pending.</strong> Management must add the separate server-side <code>OPENAI_API_KEY</code>. No key is stored in the browser.</div> : null}
      {error ? <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}

      <div className="rounded-md border border-iron-100 bg-white p-5">
        <div className="flex items-start gap-3"><Brain className="mt-0.5 h-5 w-5 text-brand-gold" /><div><h2 className="font-semibold text-iron-950">Project Brain migration</h2><p className="mt-1 text-sm leading-6 text-iron-500">Import a ChatGPT data-export ZIP or conversations JSON. Only Iron House project conversations are retained; likely secrets are redacted and unrelated chats are skipped.</p></div></div>
        <label className="mt-4 inline-flex cursor-pointer items-center gap-2 rounded-md bg-iron-950 px-4 py-2 text-sm font-semibold text-white">
          <Upload className="h-4 w-4" />{importing ? "Importing…" : "Import ChatGPT export"}
          <input className="sr-only" type="file" accept=".zip,.json,application/zip,application/json" disabled={importing} onChange={(event) => void importHistory(event.target.files?.[0])} />
        </label>
        {importMessage ? <div role="status" className="mt-3 rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">{importMessage}</div> : null}
      </div>

      <div className="rounded-md border border-iron-100 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-iron-100 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold"><ShieldCheck className="h-4 w-4" /> Audited management conversation</div>
          <span className="text-xs font-medium text-iron-500">Global hands-free control</span>
        </div>
        <div className="min-h-[360px] space-y-4 p-4" aria-live="polite">
          {messages.length === 0 ? <div className="grid min-h-[300px] place-items-center text-center"><div><Volume2 className="mx-auto h-8 w-8 text-brand-gold" /><p className="mt-3 font-semibold">Ask how to use Iron House OS</p><p className="mt-1 text-sm text-iron-500">Try “Hey Chat, where do I review project costs?”</p></div></div> : messages.map((message) => <div key={message.id} className={`max-w-3xl rounded-md p-3 text-sm leading-6 ${message.role === "user" ? "ml-auto bg-brand-gold text-brand-black" : "bg-iron-50 text-iron-800"}`}><div className="mb-1 text-xs font-semibold uppercase tracking-wide opacity-70">{message.role === "user" ? "Management" : "Iron House Chat"}</div>{message.content}</div>)}
        </div>
        <form onSubmit={(event: FormEvent) => { event.preventDefault(); void send(draft); }} className="flex gap-2 border-t border-iron-100 p-4">
          <label className="sr-only" htmlFor="iron-house-chat-message">Message Iron House Chat</label>
          <textarea id="iron-house-chat-message" value={draft} onChange={(event) => setDraft(event.target.value)} rows={2} maxLength={4000} placeholder="Ask about an OS workflow…" className="min-w-0 flex-1 resize-none rounded-md border border-iron-200 px-3 py-2 text-sm" />
          <button type="submit" disabled={sending || !draft.trim()} className="self-stretch rounded-md bg-iron-950 px-4 text-white disabled:bg-iron-300" aria-label="Send message"><Send className="h-4 w-4" /></button>
        </form>
      </div>
      <p className="text-xs text-iron-500">Enable Hey Chat once from the global control to use it across Iron House OS while this browser tab remains open. Do not enter passwords, SINs, banking, medical, or payroll information.</p>
    </section>
  );
}

function StatusCard({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md border border-iron-100 bg-white p-4"><div className="text-xs font-semibold uppercase tracking-wide text-iron-500">{label}</div><div className="mt-2 font-semibold text-iron-950">{value}</div></div>;
}
