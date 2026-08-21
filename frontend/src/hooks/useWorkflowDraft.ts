import { useCallback, useEffect, useRef, useState } from "react";

import { WorkflowType, workflowDraftsApi } from "../api/workflowDrafts";

export type DraftSaveStatus = "idle" | "loading" | "saving" | "saved" | "recovery" | "conflict" | "offline";

type RecoveryEnvelope<T> = {
  payload: T;
  savedAt: string;
};

type UseWorkflowDraftOptions<T extends Record<string, unknown>> = {
  workflowType: WorkflowType;
  title: string;
  payload: T;
  projectId?: string | null;
  ready: boolean;
  enabled: boolean;
  onRestore: (payload: T) => void;
  schemaVersion?: number;
};

function draftIdFromLocation() {
  return new URLSearchParams(window.location.search).get("draftId");
}

function replaceDraftId(draftId: string | null) {
  const url = new URL(window.location.href);
  if (draftId) url.searchParams.set("draftId", draftId);
  else url.searchParams.delete("draftId");
  window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
}

export function useWorkflowDraft<T extends Record<string, unknown>>({
  workflowType,
  title,
  payload,
  projectId = null,
  ready,
  enabled,
  onRestore,
  schemaVersion = 1,
}: UseWorkflowDraftOptions<T>) {
  const [status, setStatus] = useState<DraftSaveStatus>("idle");
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);
  const draftIdRef = useRef<string | null>(null);
  const revisionRef = useRef(0);
  const saveChainRef = useRef<Promise<void>>(Promise.resolve());
  const timeoutRef = useRef<number | null>(null);
  const onRestoreRef = useRef(onRestore);
  onRestoreRef.current = onRestore;

  const recoveryOwner = window.localStorage.getItem("ihos:draft-recovery-owner");
  const localKey = recoveryOwner
    ? `ihos:draft-recovery:${recoveryOwner}:${workflowType}`
    : `ihos:draft-recovery:${workflowType}`;
  const serializedPayload = JSON.stringify(payload);

  useEffect(() => {
    if (!ready) return;
    let active = true;
    setInitialized(false);

    async function initialize() {
      const requestedDraftId = draftIdFromLocation();
      if (requestedDraftId) {
        setStatus("loading");
        try {
          const draft = await workflowDraftsApi.get(requestedDraftId);
          if (!active || draft.workflow_type !== workflowType || draft.status !== "active") return;
          draftIdRef.current = draft.id;
          revisionRef.current = draft.revision;
          onRestoreRef.current(draft.payload as T);
          setLastSavedAt(draft.last_saved_at);
          setStatus("saved");
        } catch {
          if (!active) return;
          replaceDraftId(null);
          setStatus("offline");
        }
      } else {
        try {
          const raw = window.localStorage.getItem(localKey);
          if (raw) {
            const recovery = JSON.parse(raw) as RecoveryEnvelope<T>;
            onRestoreRef.current(recovery.payload);
            setLastSavedAt(recovery.savedAt);
            setStatus("recovery");
          }
        } catch {
          window.localStorage.removeItem(localKey);
        }
      }
      if (active) setInitialized(true);
    }

    void initialize();
    return () => { active = false; };
  }, [localKey, ready, workflowType]);

  useEffect(() => {
    if (!ready || !initialized || !enabled) return;
    const savedAt = new Date().toISOString();
    const snapshot = JSON.parse(serializedPayload) as T;
    const recovery: RecoveryEnvelope<T> = { payload: snapshot, savedAt };
    window.localStorage.setItem(localKey, JSON.stringify(recovery));

    timeoutRef.current = window.setTimeout(() => {
      saveChainRef.current = saveChainRef.current.then(async () => {
        setStatus("saving");
        try {
          const draft = draftIdRef.current
            ? await workflowDraftsApi.update(draftIdRef.current, {
                expected_revision: revisionRef.current,
                title,
                payload: snapshot,
                project_id: projectId,
                schema_version: schemaVersion,
              })
            : await workflowDraftsApi.create({
                workflow_type: workflowType,
                title,
                payload: snapshot,
                project_id: projectId,
                schema_version: schemaVersion,
              });
          draftIdRef.current = draft.id;
          revisionRef.current = draft.revision;
          replaceDraftId(draft.id);
          setLastSavedAt(draft.last_saved_at);
          setStatus("saved");
          const current = window.localStorage.getItem(localKey);
          if (current && JSON.stringify((JSON.parse(current) as RecoveryEnvelope<T>).payload) === JSON.stringify(snapshot)) {
            window.localStorage.removeItem(localKey);
          }
        } catch (reason) {
          const requestStatus = (reason as { status?: number }).status;
          setStatus(requestStatus === 409 ? "conflict" : "offline");
        }
      });
    }, 750);

    return () => {
      if (timeoutRef.current !== null) window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    };
  }, [enabled, initialized, localKey, projectId, ready, schemaVersion, serializedPayload, title, workflowType]);

  const transition = useCallback(async (kind: "cancel" | "complete") => {
    if (timeoutRef.current !== null) window.clearTimeout(timeoutRef.current);
    timeoutRef.current = null;
    await saveChainRef.current;
    try {
      if (draftIdRef.current) {
        const action = kind === "complete" ? workflowDraftsApi.complete : workflowDraftsApi.cancel;
        await action(draftIdRef.current, revisionRef.current);
      }
    } catch (reason) {
      const requestStatus = (reason as { status?: number }).status;
      setStatus(requestStatus === 409 ? "conflict" : "offline");
      return false;
    }
    draftIdRef.current = null;
    revisionRef.current = 0;
    window.localStorage.removeItem(localKey);
    replaceDraftId(null);
    setStatus("idle");
    setLastSavedAt(null);
    return true;
  }, [localKey]);

  return {
    status,
    lastSavedAt,
    completeDraft: () => transition("complete"),
    cancelDraft: () => transition("cancel"),
  };
}
