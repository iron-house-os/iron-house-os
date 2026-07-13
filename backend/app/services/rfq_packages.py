from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.models.rfq import RFQPackage, RFQPackageDocument, RFQPackageSupplierRecipient
from app.schemas.rfq_draft import RFQDraftRequest
from app.schemas.rfq_package import (
    RFQPackageBuildResponse,
    RFQPackageCreate,
    RFQPackageDocumentCreate,
    RFQPackageDocumentRead,
    RFQPackageDocumentStatus,
    RFQPackageDocumentStatusUpdate,
    RFQPackageRead,
    RFQPackageReadiness,
    RFQPackageStatus,
    RFQPackageUpdateStatus,
    RFQReadinessItem,
    RFQRecipientStatus,
    RFQScopeGenerationRequest,
    SupplierRecipientCreate,
    SupplierRecipientRead,
    SupplierRecipientStatusUpdate,
    SupplierRFQPackageDraft,
)
from app.services.rfq_drafts import build_rfq_draft


CATEGORY_SCOPE_ITEMS: dict[str, list[str]] = {
    "pipe": [
        "Provide itemized pricing for the specified pipe, fittings, couplers, and appurtenances.",
        "Confirm material standards, available lengths, lead times, and delivery requirements.",
    ],
    "aggregate": [
        "Provide unit rates by material type and source, including applicable minimum quantities.",
        "Separate material, loading, delivery, and fuel surcharge pricing.",
    ],
    "traffic": [
        "Price traffic control personnel, devices, setup, maintenance, and removal.",
        "State crew assumptions, shift rates, minimum call-outs, and plan preparation exclusions.",
    ],
    "concrete": [
        "Price the complete concrete scope including supply, placement, finishing, and curing.",
        "Separate reinforcing, formwork, pumping, testing, and winter-condition allowances.",
    ],
    "asphalt": [
        "Price paving preparation, asphalt supply, placement, compaction, and tie-ins.",
        "State mix assumptions, lift thicknesses, mobilization, and minimum-load charges.",
    ],
    "disposal": [
        "Provide disposal and haul rates by material classification and receiving facility.",
        "State testing, tipping, wait-time, minimum-load, and contaminated-material exclusions.",
    ],
}


def create_rfq_package(db: Session, payload: RFQPackageCreate) -> RFQPackageRead:
    rfq_package = RFQPackage(
        project_id=payload.project_id,
        title=payload.title,
        project_name=payload.project_name,
        scope_summary=payload.scope_summary,
        due_at=payload.due_at,
        status=RFQPackageStatus.draft.value,
        supplier_category_targets=payload.supplier_category_targets,
        metadata_json=payload.metadata,
    )
    db.add(rfq_package)
    db.commit()
    db.refresh(rfq_package)
    return _to_schema(_load_package(db, rfq_package.id))


def list_rfq_packages(db: Session) -> list[RFQPackageRead]:
    packages = db.scalars(
        select(RFQPackage)
        .options(
            selectinload(RFQPackage.recipients),
            selectinload(RFQPackage.documents),
        )
        .order_by(RFQPackage.created_at.desc())
    ).all()
    return [_to_schema(rfq_package) for rfq_package in packages]


def get_rfq_package(db: Session, rfq_package_id: UUID) -> RFQPackageRead:
    return _to_schema(_load_package(db, rfq_package_id))


def update_rfq_package_status(
    db: Session,
    rfq_package_id: UUID,
    payload: RFQPackageUpdateStatus,
) -> RFQPackageRead:
    rfq_package = _load_package(db, rfq_package_id)
    rfq_package.status = payload.status.value
    db.commit()
    return _to_schema(_load_package(db, rfq_package_id))


def select_rfq_package_suppliers(
    db: Session,
    rfq_package_id: UUID,
    payload: list[SupplierRecipientCreate],
) -> RFQPackageRead:
    rfq_package = _load_package(db, rfq_package_id)
    db.execute(
        delete(RFQPackageSupplierRecipient).where(
            RFQPackageSupplierRecipient.rfq_package_id == rfq_package_id
        )
    )

    scopes: dict[str, dict[str, object]] = {}
    for item in payload:
        scope_items = _clean_scope_items(item.scope_items) or _default_scope_items(
            item.category,
            rfq_package.scope_summary,
        )
        scopes[item.supplier_id] = {
            "items": scope_items,
            "summary": _scope_summary(scope_items),
        }
        db.add(
            RFQPackageSupplierRecipient(
                rfq_package_id=rfq_package_id,
                supplier_id=item.supplier_id,
                supplier_name=item.supplier_name,
                category=item.category,
                status=RFQRecipientStatus.pending.value,
            )
        )

    metadata = _metadata(rfq_package)
    metadata["supplier_scopes"] = scopes
    metadata["supplier_status_notes"] = {}
    rfq_package.metadata_json = metadata
    db.commit()
    return _to_schema(_load_package(db, rfq_package_id))


def generate_rfq_supplier_scopes(
    db: Session,
    rfq_package_id: UUID,
    payload: RFQScopeGenerationRequest,
) -> RFQPackageRead:
    rfq_package = _load_package(db, rfq_package_id)
    metadata = _metadata(rfq_package)
    scopes = dict(metadata.get("supplier_scopes") or {})

    for recipient in rfq_package.recipients:
        existing = scopes.get(recipient.supplier_id)
        existing_items = (
            _clean_scope_items(existing.get("items", []))
            if isinstance(existing, dict)
            else []
        )
        if payload.force or not existing_items:
            items = _default_scope_items(recipient.category, rfq_package.scope_summary)
            scopes[recipient.supplier_id] = {
                "items": items,
                "summary": _scope_summary(items),
            }

    metadata["supplier_scopes"] = scopes
    rfq_package.metadata_json = metadata
    db.commit()
    return _to_schema(_load_package(db, rfq_package_id))


def update_rfq_recipient_status(
    db: Session,
    rfq_package_id: UUID,
    recipient_id: UUID,
    payload: SupplierRecipientStatusUpdate,
) -> RFQPackageRead:
    rfq_package = _load_package(db, rfq_package_id)
    recipient = next(
        (item for item in rfq_package.recipients if item.id == recipient_id),
        None,
    )
    if recipient is None:
        raise AppError("RFQ supplier recipient not found", status_code=404)

    recipient.status = payload.status.value
    if payload.note is not None:
        metadata = _metadata(rfq_package)
        notes = dict(metadata.get("supplier_status_notes") or {})
        notes[recipient.supplier_id] = payload.note.strip() or None
        metadata["supplier_status_notes"] = notes
        rfq_package.metadata_json = metadata
    db.commit()
    return _to_schema(_load_package(db, rfq_package_id))


def register_rfq_package_documents(
    db: Session,
    rfq_package_id: UUID,
    payload: list[RFQPackageDocumentCreate],
) -> RFQPackageRead:
    _load_package(db, rfq_package_id)
    db.execute(
        delete(RFQPackageDocument).where(RFQPackageDocument.rfq_package_id == rfq_package_id)
    )
    documents: list[RFQPackageDocument] = []
    for item in payload:
        document_status = item.status
        if item.storage_uri and document_status == RFQPackageDocumentStatus.pending:
            document_status = RFQPackageDocumentStatus.attached
        if document_status == RFQPackageDocumentStatus.attached and not item.storage_uri:
            raise AppError(
                f"Attachment reference is required for '{item.title}'.",
                status_code=422,
            )
        documents.append(
            RFQPackageDocument(
                rfq_package_id=rfq_package_id,
                document_type=item.document_type,
                title=item.title,
                required=item.required,
                storage_uri=item.storage_uri,
                metadata_json=item.metadata,
                status=document_status.value,
            )
        )
    db.add_all(documents)
    db.commit()
    return _to_schema(_load_package(db, rfq_package_id))


def update_rfq_document_status(
    db: Session,
    rfq_package_id: UUID,
    document_id: UUID,
    payload: RFQPackageDocumentStatusUpdate,
) -> RFQPackageRead:
    rfq_package = _load_package(db, rfq_package_id)
    document = next(
        (item for item in rfq_package.documents if item.id == document_id),
        None,
    )
    if document is None:
        raise AppError("RFQ package document not found", status_code=404)

    storage_uri = payload.storage_uri if payload.storage_uri is not None else document.storage_uri
    if payload.status == RFQPackageDocumentStatus.attached and not storage_uri:
        raise AppError(
            f"Attachment reference is required for '{document.title}'.",
            status_code=422,
        )
    document.status = payload.status.value
    document.storage_uri = storage_uri
    db.commit()
    return _to_schema(_load_package(db, rfq_package_id))


def get_rfq_package_readiness(db: Session, rfq_package_id: UUID) -> RFQPackageReadiness:
    rfq_package = _to_schema(_load_package(db, rfq_package_id))
    required_documents = [document for document in rfq_package.documents if document.required]
    required_documents_attached = bool(required_documents) and all(
        document.status == RFQPackageDocumentStatus.attached and bool(document.storage_uri)
        for document in required_documents
    )
    supplier_scopes_ready = bool(rfq_package.recipients) and all(
        bool(recipient.scope_items) for recipient in rfq_package.recipients
    )
    items = [
        RFQReadinessItem(
            key="scope",
            label="Package scope summary",
            ready=bool(rfq_package.scope_summary),
            detail=(
                "Package scope summary is present."
                if rfq_package.scope_summary
                else "Add the overall package scope before building supplier RFQs."
            ),
        ),
        RFQReadinessItem(
            key="suppliers",
            label="Supplier recipients",
            ready=bool(rfq_package.recipients),
            detail=(
                f"{len(rfq_package.recipients)} supplier recipient(s) selected."
                if rfq_package.recipients
                else "Add at least one supplier recipient."
            ),
        ),
        RFQReadinessItem(
            key="supplier_scopes",
            label="Supplier-specific scopes",
            ready=supplier_scopes_ready,
            detail=(
                "Every supplier has a generated or edited scope."
                if supplier_scopes_ready
                else "Generate or enter scope items for every supplier."
            ),
        ),
        RFQReadinessItem(
            key="documents",
            label="Required attachments",
            ready=required_documents_attached,
            detail=(
                f"{len(required_documents)} required attachment(s) are ready."
                if required_documents_attached
                else "Attach every required drawing or document reference."
            ),
        ),
    ]
    ready_count = sum(1 for item in items if item.ready)
    return RFQPackageReadiness(
        rfq_package_id=rfq_package.id,
        status=rfq_package.status,
        ready=ready_count == len(items),
        score=round((ready_count / len(items)) * 100),
        items=items,
    )


def build_rfq_supplier_packages(
    db: Session,
    rfq_package_id: UUID,
) -> RFQPackageBuildResponse:
    rfq_package = _to_schema(_load_package(db, rfq_package_id))
    readiness = get_rfq_package_readiness(db, rfq_package_id)
    attachment_names = [
        document.title
        for document in rfq_package.documents
        if document.status == RFQPackageDocumentStatus.attached
    ]
    packages: list[SupplierRFQPackageDraft] = []

    for recipient in rfq_package.recipients:
        draft = build_rfq_draft(
            RFQDraftRequest(
                project_name=rfq_package.project_name or rfq_package.title,
                quote_return_deadline=rfq_package.due_at,
                category=recipient.category or "Supplier pricing",
                supplier_name=recipient.supplier_name,
                scope_items=recipient.scope_items,
                attachment_names=attachment_names,
            )
        )
        packages.append(
            SupplierRFQPackageDraft(
                recipient_id=recipient.id,
                supplier_id=recipient.supplier_id,
                supplier_name=recipient.supplier_name,
                category=recipient.category,
                status=recipient.status,
                subject=draft.subject,
                body=draft.body,
                scope_items=recipient.scope_items,
                attachment_names=draft.attachment_names,
            )
        )

    return RFQPackageBuildResponse(
        rfq_package_id=rfq_package.id,
        ready=readiness.ready,
        blockers=[item.detail for item in readiness.items if not item.ready],
        packages=packages,
    )


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


def _scope_for(rfq_package: RFQPackage, supplier_id: str) -> tuple[list[str], str | None]:
    metadata = _metadata(rfq_package)
    scopes = metadata.get("supplier_scopes") or {}
    value = scopes.get(supplier_id) if isinstance(scopes, dict) else None
    if not isinstance(value, dict):
        return [], None
    items = _clean_scope_items(value.get("items", []))
    summary = value.get("summary")
    return items, str(summary) if summary else None


def _status_note_for(rfq_package: RFQPackage, supplier_id: str) -> str | None:
    notes = _metadata(rfq_package).get("supplier_status_notes") or {}
    if not isinstance(notes, dict):
        return None
    note = notes.get(supplier_id)
    return str(note) if note else None


def _clean_scope_items(items: object) -> list[str]:
    if not isinstance(items, list):
        return []
    return [str(item).strip() for item in items if str(item).strip()]


def _default_scope_items(category: str | None, package_scope: str | None) -> list[str]:
    normalized = (category or "").strip().casefold()
    template = next(
        (
            items
            for keyword, items in CATEGORY_SCOPE_ITEMS.items()
            if keyword in normalized
        ),
        [
            "Price the complete applicable supplier or subcontractor scope.",
            "Separate labour, material, equipment, delivery, mobilization, and taxes where applicable.",
        ],
    )
    items = list(template)
    if package_scope:
        items.insert(0, f"Base pricing on this package scope: {package_scope.strip()}")
    items.append(
        "State exclusions, assumptions, lead time, quote validity, and proposed substitutions."
    )
    return items


def _scope_summary(items: list[str]) -> str | None:
    return " ".join(items) if items else None


def _recipient_status(raw_status: str) -> RFQRecipientStatus:
    if raw_status == "selected":
        return RFQRecipientStatus.pending
    return RFQRecipientStatus(raw_status)


def _document_status(document: RFQPackageDocument) -> RFQPackageDocumentStatus:
    if document.status == "registered":
        return (
            RFQPackageDocumentStatus.attached
            if document.storage_uri
            else RFQPackageDocumentStatus.pending
        )
    return RFQPackageDocumentStatus(document.status)


def _to_schema(rfq_package: RFQPackage) -> RFQPackageRead:
    return RFQPackageRead(
        id=rfq_package.id,
        project_id=rfq_package.project_id,
        title=rfq_package.title,
        project_name=rfq_package.project_name,
        scope_summary=rfq_package.scope_summary,
        due_at=rfq_package.due_at,
        status=RFQPackageStatus(rfq_package.status),
        supplier_category_targets=rfq_package.supplier_category_targets or [],
        metadata=rfq_package.metadata_json or {},
        recipients=[
            SupplierRecipientRead(
                id=recipient.id,
                supplier_id=recipient.supplier_id,
                supplier_name=recipient.supplier_name,
                category=recipient.category,
                status=_recipient_status(recipient.status),
                scope_items=_scope_for(rfq_package, recipient.supplier_id)[0],
                scope_summary=_scope_for(rfq_package, recipient.supplier_id)[1],
                status_note=_status_note_for(rfq_package, recipient.supplier_id),
            )
            for recipient in rfq_package.recipients
        ],
        documents=[
            RFQPackageDocumentRead(
                id=document.id,
                document_type=document.document_type,
                title=document.title,
                required=document.required,
                status=_document_status(document),
                storage_uri=document.storage_uri,
                metadata=document.metadata_json or {},
            )
            for document in rfq_package.documents
        ],
        created_at=rfq_package.created_at,
        updated_at=rfq_package.updated_at,
    )
