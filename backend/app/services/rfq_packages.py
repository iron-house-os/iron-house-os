from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.models.rfq import RFQPackage, RFQPackageDocument, RFQPackageSupplierRecipient
from app.schemas.rfq_package import (
    RFQPackageCreate,
    RFQPackageDocumentCreate,
    RFQPackageDocumentRead,
    RFQPackageRead,
    RFQPackageReadiness,
    RFQPackageStatus,
    RFQPackageUpdateStatus,
    RFQReadinessItem,
    SupplierRecipientCreate,
    SupplierRecipientRead,
)


def create_rfq_package(db: Session, payload: RFQPackageCreate) -> RFQPackageRead:
    rfq_package = RFQPackage(
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
    _load_package(db, rfq_package_id)
    db.execute(
        delete(RFQPackageSupplierRecipient).where(
            RFQPackageSupplierRecipient.rfq_package_id == rfq_package_id
        )
    )
    db.add_all(
        RFQPackageSupplierRecipient(
            rfq_package_id=rfq_package_id,
            supplier_id=item.supplier_id,
            supplier_name=item.supplier_name,
            category=item.category,
            status="selected",
        )
        for item in payload
    )
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
    db.add_all(
        RFQPackageDocument(
            rfq_package_id=rfq_package_id,
            document_type=item.document_type,
            title=item.title,
            required=item.required,
            storage_uri=item.storage_uri,
            metadata_json=item.metadata,
            status="registered",
        )
        for item in payload
    )
    db.commit()
    return _to_schema(_load_package(db, rfq_package_id))


def get_rfq_package_readiness(db: Session, rfq_package_id: UUID) -> RFQPackageReadiness:
    rfq_package = _to_schema(_load_package(db, rfq_package_id))
    required_documents = [document for document in rfq_package.documents if document.required]
    required_documents_registered = bool(required_documents) and all(
        document.status == "registered" for document in required_documents
    )
    items = [
        RFQReadinessItem(
            key="scope",
            label="Scope summary",
            ready=bool(rfq_package.scope_summary),
            detail="Scope summary is present."
            if rfq_package.scope_summary
            else "Add a scope summary before issuing.",
        ),
        RFQReadinessItem(
            key="suppliers",
            label="Supplier recipients",
            ready=bool(rfq_package.recipients),
            detail=f"{len(rfq_package.recipients)} supplier recipients selected.",
        ),
        RFQReadinessItem(
            key="documents",
            label="Required bid documents",
            ready=required_documents_registered,
            detail=f"{len(required_documents)} required documents registered.",
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


def _to_schema(rfq_package: RFQPackage) -> RFQPackageRead:
    return RFQPackageRead(
        id=rfq_package.id,
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
                status=recipient.status,
            )
            for recipient in rfq_package.recipients
        ],
        documents=[
            RFQPackageDocumentRead(
                id=document.id,
                document_type=document.document_type,
                title=document.title,
                required=document.required,
                status=document.status,
                storage_uri=document.storage_uri,
                metadata=document.metadata_json or {},
            )
            for document in rfq_package.documents
        ],
        created_at=rfq_package.created_at,
        updated_at=rfq_package.updated_at,
    )
