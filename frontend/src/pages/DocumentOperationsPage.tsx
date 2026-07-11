import { useState } from "react";

import { DocumentAuditPanel } from "../components/DocumentAuditPanel";
import { DocumentUploadPanel } from "../components/DocumentUploadPanel";
import { ProjectDocumentBrowser } from "../components/ProjectDocumentBrowser";
import { RFQAttachmentManifestPanel } from "../components/RFQAttachmentManifestPanel";

export function DocumentOperationsPage() {
  const [projectId, setProjectId] = useState("");

  return (
    <section className="space-y-6">
      <div className="border-b border-iron-100 pb-6">
        <h1 className="text-3xl font-semibold text-iron-950">Document Operations</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-iron-500">
          Upload, browse, secure, audit, and package project documents for estimating and RFQ workflows.
        </p>
      </div>

      <div className="rounded-md border border-iron-100 bg-white p-5">
        <label className="grid gap-1 text-sm">
          <span className="font-medium text-iron-700">Project ID</span>
          <input value={projectId} onChange={(event) => setProjectId(event.target.value)} className="rounded-md border border-iron-100 px-3 py-2" placeholder="Paste project UUID" />
        </label>
      </div>

      <DocumentUploadPanel projectId={projectId || null} />
      <ProjectDocumentBrowser projectId={projectId || null} />
      <RFQAttachmentManifestPanel />
      <DocumentAuditPanel />
    </section>
  );
}
