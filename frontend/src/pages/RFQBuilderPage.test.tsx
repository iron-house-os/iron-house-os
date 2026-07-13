import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RFQBuilderPage } from "./RFQBuilderPage";

const requests: Array<{ url: string; method: string; body: unknown }> = [];

let packageState: Record<string, any>;
let attachmentsReady = false;
let workflowState: Record<string, any>;

function resetPackage() {
  attachmentsReady = false;
  packageState = {
    id: "rfq-1",
    project_id: null,
    title: "Stormwater Pipe RFQ",
    project_name: "King George Utility Upgrade",
    scope_summary: "Supply pipe and appurtenances.",
    due_at: "2026-07-20T16:00:00Z",
    status: "assembling",
    supplier_category_targets: ["pipe"],
    metadata: {},
    recipients: [],
    documents: [],
    created_at: "2026-07-13T10:00:00Z",
    updated_at: "2026-07-13T10:00:00Z",
  };
  workflowState = {
    rfq_package_id: "rfq-1",
    status: "preview_only",
    prepared_at: null,
    stale: false,
    drive_package: null,
    gmail_drafts: [],
    supplier_responses: [],
    blockers: [],
    external_actions_performed: false,
    send_requires_approval: true,
  };
}

function readiness() {
  const suppliersReady = packageState.recipients.length > 0;
  return {
    rfq_package_id: "rfq-1",
    status: packageState.status,
    ready: suppliersReady && attachmentsReady,
    score: suppliersReady && attachmentsReady ? 100 : suppliersReady ? 75 : 25,
    items: [
      { key: "scope", label: "Package scope summary", ready: true, detail: "Scope ready." },
      { key: "suppliers", label: "Supplier recipients", ready: suppliersReady, detail: "Recipients." },
      { key: "supplier_scopes", label: "Supplier-specific scopes", ready: suppliersReady, detail: "Scopes." },
      { key: "documents", label: "Required attachments", ready: attachmentsReady, detail: "Attachments." },
    ],
  };
}

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("RFQBuilderPage", () => {
  beforeEach(() => {
    requests.length = 0;
    resetPackage();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const method = init?.method ?? "GET";
        const body = init?.body ? JSON.parse(String(init.body)) : null;
        requests.push({ url, method, body });

        if (url.endsWith("/rfqs") && method === "GET") {
          return jsonResponse({ items: [packageState], total: 1 });
        }
        if (url.endsWith("/rfqs/rfq-1/readiness")) {
          return jsonResponse(readiness());
        }
        if (url.endsWith("/rfqs/rfq-1/communication-workflow") && method === "GET") {
          return jsonResponse(workflowState);
        }
        if (url.endsWith("/rfqs/rfq-1") && method === "GET") {
          return jsonResponse(packageState);
        }
        if (url.endsWith("/rfqs/rfq-1/suppliers") && method === "PUT") {
          packageState = {
            ...packageState,
            recipients: body.map((supplier: Record<string, any>, index: number) => ({
              ...supplier,
              id: `recipient-${index + 1}`,
              scope_items: supplier.scope_items.length
                ? supplier.scope_items
                : [
                    "Provide itemized pricing for the specified pipe and fittings.",
                    "Confirm lead time and delivery.",
                  ],
              scope_summary: "Generated pipe scope.",
              status: "pending",
              status_note: null,
            })),
          };
          return jsonResponse(packageState);
        }
        if (url.includes("/suppliers/recipient-1/status") && method === "PATCH") {
          packageState = {
            ...packageState,
            recipients: packageState.recipients.map((recipient: Record<string, any>) =>
              recipient.id === "recipient-1"
                ? { ...recipient, status: body.status, status_note: body.note }
                : recipient,
            ),
          };
          return jsonResponse(packageState);
        }
        if (url.endsWith("/rfqs/rfq-1/documents") && method === "PUT") {
          attachmentsReady = true;
          packageState = {
            ...packageState,
            documents: body.map((document: Record<string, any>, index: number) => ({
              ...document,
              id: `document-${index + 1}`,
            })),
          };
          return jsonResponse(packageState);
        }
        if (url.endsWith("/rfqs/rfq-1/build") && method === "POST") {
          return jsonResponse({
            rfq_package_id: "rfq-1",
            ready: true,
            blockers: [],
            packages: [
              {
                recipient_id: "recipient-1",
                supplier_id: packageState.recipients[0].supplier_id,
                supplier_name: "Pacific Pipe Supply",
                category: "pipe",
                status: "sent",
                subject: "RFQ - King George Utility Upgrade - pipe - Pacific Pipe Supply",
                body: "Hello,\n\nPlease price the generated pipe scope.",
                scope_items: packageState.recipients[0].scope_items,
                attachment_names: ["Civil drawings", "Project specifications"],
              },
            ],
          });
        }
        if (url.endsWith("/rfqs/rfq-1/communication-workflow/prepare") && method === "POST") {
          workflowState = {
            ...workflowState,
            prepared_at: "2026-07-13T15:40:00Z",
            drive_package: {
              folder_uri: body.drive_folder_uri,
              manifest_uri: body.drive_manifest_uri ?? null,
              reusable: true,
              document_references: packageState.documents.map(
                (document: Record<string, any>) => document.storage_uri,
              ),
              saved_at: "2026-07-13T15:40:00Z",
              source_fingerprint: "fingerprint-1",
            },
            gmail_drafts: [
              {
                recipient_id: "recipient-1",
                supplier_id: packageState.recipients[0].supplier_id,
                supplier_name: packageState.recipients[0].supplier_name,
                to: packageState.recipients[0].recipient_email,
                subject: "RFQ - King George Utility Upgrade - pipe - Pacific Pipe Supply",
                body: "Hello, draft only.",
                attachment_references: packageState.documents.map(
                  (document: Record<string, any>) => document.storage_uri,
                ),
                status: "preview_only",
                ready_for_draft_creation: true,
                send_approved: false,
              },
            ],
          };
          return jsonResponse(workflowState);
        }
        if (url.endsWith("/rfqs/rfq-1/supplier-responses") && method === "POST") {
          workflowState = {
            ...workflowState,
            supplier_responses: [
              ...workflowState.supplier_responses,
              {
                id: "response-1",
                supplier_id: body.supplier_id,
                supplier_name: "Pacific Pipe Supply",
                received_at: "2026-07-13T15:45:00Z",
                recorded_at: "2026-07-13T15:45:00Z",
                gmail_thread_uri: body.gmail_thread_uri ?? null,
                drive_file_uri: body.drive_file_uri ?? null,
                notes: body.notes ?? null,
              },
            ],
          };
          packageState = {
            ...packageState,
            recipients: packageState.recipients.map((recipient: Record<string, any>) => ({
              ...recipient,
              status: recipient.supplier_id === body.supplier_id ? "replied" : recipient.status,
              status_note: recipient.supplier_id === body.supplier_id ? body.notes : recipient.status_note,
            })),
          };
          return jsonResponse(workflowState, 201);
        }
        throw new Error(`Unexpected request: ${method} ${url}`);
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("builds supplier scopes, attachment checklist, tracking, and draft packages", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/rfq-builder/rfq-1?projectName=King%20George"]}>
        <Routes>
          <Route path="/rfq-builder/:rfqPackageId" element={<RFQBuilderPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByLabelText("Supplier 1 name")).toBeInTheDocument();
    expect(
      screen.getByText("Draft-only workflow: building or changing tracking status does not send email or contact suppliers."),
    ).toBeInTheDocument();

    await user.type(screen.getByLabelText("Supplier 1 name"), "Pacific Pipe Supply");
    await user.type(screen.getByLabelText("Supplier 1 category"), "pipe");
    await user.type(
      screen.getByLabelText("Supplier 1 email"),
      "estimating@pacific-pipe.example",
    );
    await user.click(screen.getByRole("button", { name: "Save suppliers and scopes" }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.url.endsWith("/rfqs/rfq-1/suppliers")
            && request.method === "PUT",
        ),
      ).toBe(true);
    });
    expect(
      requests.find(
        (request) =>
          request.url.endsWith("/rfqs/rfq-1/suppliers")
          && request.method === "PUT",
      )?.body,
    ).toEqual([
      expect.objectContaining({
        supplier_name: "Pacific Pipe Supply",
        category: "pipe",
      }),
    ]);
    expect(
      await screen.findByLabelText("Pacific Pipe Supply tracking status"),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect((screen.getByLabelText("Supplier 1 scope items") as HTMLTextAreaElement).value)
        .toContain("Provide itemized pricing");
    });
    expect(screen.getAllByText("Pacific Pipe Supply").length).toBeGreaterThan(0);

    await user.selectOptions(
      screen.getByLabelText("Pacific Pipe Supply tracking status"),
      "sent",
    );
    await user.type(
      screen.getByLabelText("Pacific Pipe Supply tracking note"),
      "Issued manually at 09:00.",
    );
    await user.click(screen.getByRole("button", { name: "Save status" }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.url.includes("/suppliers/recipient-1/status")
            && (request.body as Record<string, unknown>).status === "sent",
        ),
      ).toBe(true);
    });

    await user.selectOptions(screen.getByLabelText("Document 1 status"), "attached");
    await user.type(
      screen.getByLabelText("Document 1 attachment reference"),
      "drive://projects/kg/civil-drawings.pdf",
    );
    await user.selectOptions(screen.getByLabelText("Document 2 status"), "attached");
    await user.type(
      screen.getByLabelText("Document 2 attachment reference"),
      "drive://projects/kg/specifications.pdf",
    );
    await user.click(screen.getByRole("button", { name: "Save attachment checklist" }));

    await waitFor(() => expect(screen.getByText("100%")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "Build draft packages" }));

    expect(
      await screen.findByText("Package is ready for manual review and issue."),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Pacific Pipe Supply — RFQ - King George Utility Upgrade - pipe - Pacific Pipe Supply",
      ),
    ).toBeInTheDocument();

    await user.type(
      screen.getByLabelText("Drive package folder reference"),
      "drive://projects/kg/rfq/stormwater",
    );
    await user.type(
      screen.getByLabelText("Workflow sender email"),
      "estimating@ironhouse.example",
    );
    await user.click(screen.getByRole("button", { name: "Save reusable draft workflow" }));

    expect(
      await screen.findByText("Preview-only workflow saved. No Gmail or Drive action was performed."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Ready for separately approved draft creation"),
    ).toBeInTheDocument();

    await user.type(
      screen.getByLabelText("Drive response file reference"),
      "drive://projects/kg/responses/pacific-pipe.pdf",
    );
    await user.type(
      screen.getByLabelText("Response notes"),
      "Quote received and saved.",
    );
    await user.click(screen.getByRole("button", { name: "Record response reference" }));

    expect(await screen.findByText("Quote received and saved.")).toBeInTheDocument();

    const supplierRequest = requests.find(
      (request) => request.url.endsWith("/rfqs/rfq-1/suppliers") && request.method === "PUT",
    );
    expect(supplierRequest?.body).toEqual([
      expect.objectContaining({
        supplier_name: "Pacific Pipe Supply",
        category: "pipe",
        recipient_email: "estimating@pacific-pipe.example",
        scope_items: [],
      }),
    ]);
    expect(
      requests.some(
        (request) =>
          request.url.endsWith("/communication-workflow/prepare")
          && request.method === "POST",
      ),
    ).toBe(true);
    expect(
      requests.some(
        (request) =>
          request.url.endsWith("/supplier-responses")
          && request.method === "POST",
      ),
    ).toBe(true);
  });
});
