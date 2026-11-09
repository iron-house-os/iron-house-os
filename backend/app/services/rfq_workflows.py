from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.models.rfq import RFQPackage
from app.schemas.rfq_draft import RFQDraftRequest
from app.schemas.rfq_package import RFQPackageDocumentStatus, RFQRecipientStatus
from app.schemas.rfq_workflow import (
    DrivePackageRecord,
    GmailDraftPlan,
    RFQCommunicationWorkflow,
    RFQWorkflowPrepareRequest,
    SupplierResponseCreate,
    SupplierResponseRecord,
)
from app.services.rfq_drafts import build_rfq_draft
from app.services.rfq_packages import build_rfq_supplier_packages


WORKFLOW_METADATA_KEY = "gmail_drive_workflow"
RESPONSE_METADATA_KEY = "supplier_responses"


def get_rfq_communication_workflow(
    db: Session,
    rfq_package_id: UUID,
) -> RFQCommunicationWorkflow:
    rfq_package = _load_package(db, rfq_package_id)
    metadata = _metadata(rfq_package)
    stored = metadata.get(WORKFLOW_METADATA_KEY) or {}
    drive_payload = stored.get("drive_package") if isinstance(stored, dict) else None
    drive_package = (
        DrivePackageRecord.model_validate(drive_payload)
        if isinstance(drive_payload, dict)
        else None
    )
    gmail_payloads = stored.get("gmail_drafts", []) if isinstance(stored, dict) else []
    response_payloads = metadata.get(RESPONSE_METADATA_KEY) or []
    return RFQCommunicationWorkflow(
        rfq_package_id=rfq_package.id,
        prepared_at=stored.get("prepared_at") if isinstance(stored, dict) else None,
        stale=(
            drive_package is not None
            and drive_package.source_fingerprint != _source_fingerprint(rfq_package)
        ),
        drive_package=drive_package,
        gmail_drafts=[
            GmailDraftPlan.model_validate(item)
            for item in gmail_payloads
            if isinstance(item, dict)
        ],
        supplier_responses=[
            SupplierResponseRecord.model_validate(item)
            for item in response_payloads
            if isinstance(item, dict)
        ],
        blockers=(
            [str(item) for item in stored.get("blockers", [])]
            if isinstance(stored, dict)
            else []
        ),
    )


def prepare_rfq_communication_workflow(
    db: Session,
    rfq_package_id: UUID,
    payload: RFQWorkflowPrepareRequest,
) -> RFQCommunicationWorkflow:
    if not payload.drive_folder_uri.strip():
        raise AppError("A Drive folder reference is required.", status_code=422)

    rfq_package = _load_package(db, rfq_package_id)
    build = build_rfq_supplier_packages(db, rfq_package_id)
    attachment_references = sorted(
        {
            document.storage_uri
            for document in rfq_package.documents
            if document.status in {"attached", "registered"} and document.storage_uri
        }
    )
    blockers = list(build.blockers)
    gmail_drafts: list[GmailDraftPlan] = []
    for draft in build.packages:
        if not draft.recipient_email:
            blockers.append(f"Add a recipient email for {draft.supplier_name}.")
        email_draft = build_rfq_draft(
            RFQDraftRequest(
                project_name=rfq_package.project_name or rfq_package.title,
                quote_return_deadline=rfq_package.due_at,
                category=draft.category or "Supplier pricing",
                supplier_name=draft.supplier_name,
                recipient_email=draft.recipient_email,
                scope_items=draft.scope_items,
                attachment_names=draft.attachment_names,
                sender_name=payload.sender_name,
                sender_email=payload.sender_email,
                sender_phone=payload.sender_phone,
            )
        )
        gmail_drafts.append(
            GmailDraftPlan(
                recipient_id=draft.recipient_id,
                supplier_id=draft.supplier_id,
                supplier_name=draft.supplier_name,
                to=draft.recipient_email,
                subject=email_draft.subject,
                body=email_draft.body,
                attachment_references=attachment_references,
                ready_for_draft_creation=build.ready and bool(draft.recipient_email),
            )
        )

    now = datetime.now(timezone.utc)
    drive_package = DrivePackageRecord(
        folder_uri=payload.drive_folder_uri.strip(),
        manifest_uri=(payload.drive_manifest_uri or "").strip() or None,
        document_references=attachment_references,
        saved_at=now,
        source_fingerprint=_source_fingerprint(rfq_package),
    )
    metadata = _metadata(rfq_package)
    metadata[WORKFLOW_METADATA_KEY] = {
        "prepared_at": now.isoformat(),
        "drive_package": drive_package.model_dump(mode="json"),
        "gmail_drafts": [item.model_dump(mode="json") for item in gmail_drafts],
        "blockers": list(dict.fromkeys(blockers)),
        "sender": {
            "name": payload.sender_name,
            "email": str(payload.sender_email) if payload.sender_email else None,
            "phone": payload.sender_phone,
        },
    }
    rfq_package.metadata_json = metadata
    db.commit()
    return get_rfq_communication_workflow(db, rfq_package_id)


def record_supplier_response(
    db: Session,
    rfq_package_id: UUID,
    payload: SupplierResponseCreate,
) -> RFQCommunicationWorkflow:
    if not (payload.gmail_thread_uri or "").strip() and not (
        payload.drive_file_uri or ""
    ).strip():
        raise AppError(
            "A Gmail thread or Drive file reference is required.",
            status_code=422,
        )

    rfq_package = _load_package(db, rfq_package_id)
    recipient = next(
        (
            item
            for item in rfq_package.recipients
            if item.supplier_id == payload.supplier_id
        ),
        None,
    )
    if recipient is None:
        raise AppError("RFQ supplier recipient not found", status_code=404)

    now = datetime.now(timezone.utc)
    record = SupplierResponseRecord(
        id=uuid4(),
        supplier_id=recipient.supplier_id,
        supplier_name=recipient.supplier_name,
        received_at=payload.received_at or now,
        recorded_at=now,
        gmail_thread_uri=(payload.gmail_thread_uri or "").strip() or None,
        drive_file_uri=(payload.drive_file_uri or "").strip() or None,
        notes=(payload.notes or "").strip() or None,
    )
    metadata = _metadata(rfq_package)
    responses = list(metadata.get(RESPONSE_METADATA_KEY) or [])
    responses.append(record.model_dump(mode="json"))
    metadata[RESPONSE_METADATA_KEY] = responses
    notes = dict(metadata.get("supplier_status_notes") or {})
    notes[recipient.supplier_id] = record.notes or "Supplier response recorded."
    metadata["supplier_status_notes"] = notes
    rfq_package.metadata_json = metadata
    recipient.status = RFQRecipientStatus.replied.value
    db.commit()
    return get_rfq_communication_workflow(db, rfq_package_id)


def _load_package(db: Session, rfq_package_id: UUID) -> RFQPackage:
    rfq_package = db.scalar(
        select(RFQPackage)
        .where(RFQPackage.id == rfq_package_id)
        .options(
            selectinload(RFQPackage.recipients),
            selectinload(RFQPackage.documents),
        )
    )
    if rfq_package is None:
        raise AppError("RFQ package not found", status_code=404)
    return rfq_package


def _metadata(rfq_package: RFQPackage) -> dict:
    return dict(rfq_package.metadata_json or {})


def _recipient_email(rfq_package: RFQPackage, supplier_id: str) -> str | None:
    contacts = _metadata(rfq_package).get("supplier_contacts") or {}
    if not isinstance(contacts, dict):
        return None
    contact = contacts.get(supplier_id)
    if not isinstance(contact, dict):
        return None
    value = contact.get("recipient_email")
    return str(value) if value else None


def _supplier_scope(rfq_package: RFQPackage, supplier_id: str) -> list[str]:
    scopes = _metadata(rfq_package).get("supplier_scopes") or {}
    scope = scopes.get(supplier_id) if isinstance(scopes, dict) else None
    items = scope.get("items", []) if isinstance(scope, dict) else []
    return [str(item) for item in items] if isinstance(items, list) else []


def _source_fingerprint(rfq_package: RFQPackage) -> str:
    source = {
        "title": rfq_package.title,
        "project_name": rfq_package.project_name,
        "scope_summary": rfq_package.scope_summary,
        "due_at": rfq_package.due_at.isoformat() if rfq_package.due_at else None,
        "recipients": sorted(
            [
                {
                    "supplier_id": item.supplier_id,
                    "supplier_name": item.supplier_name,
                    "category": item.category,
                    "recipient_email": _recipient_email(rfq_package, item.supplier_id),
                    "scope_items": _supplier_scope(rfq_package, item.supplier_id),
                }
                for item in rfq_package.recipients
            ],
            key=lambda item: str(item["supplier_id"]),
        ),
        "documents": sorted(
            [
                {
                    "title": item.title,
                    "status": (
                        RFQPackageDocumentStatus.attached.value
                        if item.status == "registered" and item.storage_uri
                        else item.status
                    ),
                    "storage_uri": item.storage_uri,
                }
                for item in rfq_package.documents
            ],
            key=lambda item: str(item["title"]),
        ),
    }
    encoded = json.dumps(source, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()
