from datetime import datetime, time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.document import Document
from app.models.project import Project
from app.models.rfq import RFQPackage, RFQPackageDocument
from app.models.tender import Tender
from app.schemas.document import DocumentStatus
from app.schemas.project import ProjectStatus
from app.schemas.rfq_package import RFQPackageStatus
from app.schemas.tender import (
    TenderCreate,
    TenderIntakeCreate,
    TenderIntakeRead,
    TenderList,
    TenderRead,
    TenderStatus,
    TenderUpdate,
)
from app.services.documents import _to_schema as document_to_schema
from app.services.projects import _to_schema as project_to_schema
from app.services.rfq_packages import _to_schema as rfq_package_to_schema

KEYWORD_CATEGORY_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("water", "sewer", "storm", "pipe", "main", "utility"), "pipe and fittings"),
    (("concrete", "curb", "sidewalk", "letdown"), "concrete"),
    (("asphalt", "paving", "mill", "overlay"), "paving"),
    (("traffic", "detour", "lane closure"), "traffic control"),
    (("electrical", "streetlight", "signal", "lighting"), "electrical"),
    (("geotechnical", "soil", "excavation", "earthworks"), "earthworks"),
    (("landscape", "irrigation", "planting"), "landscaping"),
)

DOCUMENT_CATEGORY_RULES: dict[str, str] = {
    "drawing": "civil drawings",
    "specification": "civil general contractor",
    "geotechnical": "geotechnical",
    "traffic_control": "traffic control",
    "environmental": "environmental",
    "permit": "permits",
    "quote_request": "supplier quotes",
}

LEGACY_TENDER_STATUS_MAP: dict[str, TenderStatus] = {
    "watching": TenderStatus.new,
    "watchlist": TenderStatus.new,
    "draft": TenderStatus.new,
    "open": TenderStatus.new,
    "shortlisted": TenderStatus.reviewing,
    "qualified": TenderStatus.reviewing,
    "review": TenderStatus.reviewing,
    "bid": TenderStatus.bidding,
    "pricing": TenderStatus.bidding,
    "active": TenderStatus.bidding,
    "won": TenderStatus.awarded,
    "declined": TenderStatus.no_bid,
    "no bid": TenderStatus.no_bid,
    "closed": TenderStatus.no_bid,
}


def create_tender(db: Session, payload: TenderCreate) -> TenderRead:
    tender = Tender(**_tender_values(payload))
    db.add(tender)
    db.commit()
    return _to_schema(_load_tender(db, tender.id))


def list_tenders(db: Session, status: str | None = None) -> TenderList:
    statement = select(Tender).order_by(Tender.created_at.desc())
    if status:
        statement = statement.where(Tender.status == status)
    items = [_to_schema(tender) for tender in db.scalars(statement).all()]
    return TenderList(items=items, total=len(items))


def get_tender(db: Session, tender_id: UUID) -> TenderRead:
    return _to_schema(_load_tender(db, tender_id))


def update_tender(db: Session, tender_id: UUID, payload: TenderUpdate) -> TenderRead:
    tender = _load_tender(db, tender_id)
    for key, value in _tender_values(payload).items():
        setattr(tender, key, value)
    db.commit()
    return _to_schema(_load_tender(db, tender_id))


def intake_tender(db: Session, payload: TenderIntakeCreate) -> TenderIntakeRead:
    suggested_categories = suggest_supplier_categories(
        description=payload.description,
        document_categories=[document.category.value for document in payload.documents],
    )
    project = Project(
        name=payload.title,
        client_owner=payload.owner,
        municipality_name=payload.municipality,
        tender_number=payload.tender_number,
        tender_source=payload.source,
        tender_closing_date=payload.closing_date,
        bid_due_date=payload.closing_date,
        project_address=payload.project_address,
        contract_value=payload.estimated_value,
        status=ProjectStatus.opportunity.value,
        notes=payload.description,
        metadata_json={"source": "tender_intake"},
    )
    db.add(project)
    db.flush()

    rfq_package = RFQPackage(
        project_id=project.id,
        title=f"{payload.title} RFQ Package",
        project_name=project.name,
        scope_summary=payload.description,
        due_at=_date_to_datetime(payload.closing_date),
        status=RFQPackageStatus.draft.value,
        supplier_category_targets=suggested_categories,
        metadata_json={"source": "tender_intake"},
    )
    db.add(rfq_package)
    db.flush()

    tender = Tender(
        **_tender_values(payload),
        project_id=project.id,
        rfq_package_id=rfq_package.id,
    )
    tender.metadata_json = {
        **(payload.metadata or {}),
        "suggested_supplier_categories": suggested_categories,
    }
    db.add(tender)
    db.flush()

    documents = [
        Document(
            title=document.title,
            category=document.category.value,
            status=DocumentStatus.registered.value,
            project_id=project.id,
            rfq_package_id=rfq_package.id,
            tender_id=tender.id,
            storage_uri=document.storage_uri,
            description=document.description,
            metadata_json={**document.metadata, "source": "tender_intake"},
        )
        for document in payload.documents
    ]
    db.add_all(documents)
    db.flush()

    db.add_all(
        RFQPackageDocument(
            rfq_package_id=rfq_package.id,
            document_type=document.category,
            title=document.title,
            required=True,
            storage_uri=document.storage_uri,
            metadata_json={"source_document_id": str(document.id), "source": "tender_intake"},
            status="registered",
        )
        for document in documents
    )
    db.commit()

    return TenderIntakeRead(
        tender=_to_schema(_load_tender(db, tender.id)),
        project=project_to_schema(project),
        rfq_package=rfq_package_to_schema(rfq_package),
        documents=[document_to_schema(document) for document in documents],
        suggested_supplier_categories=suggested_categories,
    )


def suggest_supplier_categories(
    description: str | None,
    document_categories: list[str],
) -> list[str]:
    suggestions: list[str] = []
    for category in document_categories:
        mapped = DOCUMENT_CATEGORY_RULES.get(category)
        if mapped:
            suggestions.append(mapped)

    text = (description or "").lower()
    for keywords, category in KEYWORD_CATEGORY_RULES:
        if any(keyword in text for keyword in keywords):
            suggestions.append(category)

    return sorted(set(suggestions))


def _load_tender(db: Session, tender_id: UUID) -> Tender:
    tender = db.get(Tender, tender_id)
    if tender is None:
        raise AppError("Tender not found", status_code=404)
    return tender


def _tender_values(payload: TenderCreate | TenderUpdate | TenderIntakeCreate) -> dict:
    data = payload.model_dump(exclude={"metadata", "documents"}, exclude_unset=True)
    if "municipality" in data:
        data["municipality_name"] = data.pop("municipality")
    status = data.get("status")
    if status is not None:
        data["status"] = status.value
    if "metadata" in payload.model_fields_set or isinstance(
        payload,
        TenderCreate | TenderIntakeCreate,
    ):
        data["metadata_json"] = payload.metadata or {}
    return data


def _date_to_datetime(value) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time(hour=17))


def _to_schema(tender: Tender) -> TenderRead:
    return TenderRead(
        id=tender.id,
        project_id=tender.project_id,
        rfq_package_id=tender.rfq_package_id,
        title=tender.title,
        tender_number=tender.tender_number,
        source=tender.source,
        source_url=tender.source_url,
        owner=tender.owner,
        municipality=tender.municipality_name,
        closing_date=tender.closing_date,
        site_meeting_date=tender.site_meeting_date,
        question_deadline=tender.question_deadline,
        project_address=tender.project_address,
        description=tender.description,
        status=_read_tender_status(tender.status),
        estimated_value=(
            float(tender.estimated_value) if tender.estimated_value is not None else None
        ),
        metadata=tender.metadata_json or {},
        document_ids=tender_document_ids(tender),
        suggested_supplier_categories=(
            (tender.metadata_json or {}).get("suggested_supplier_categories", [])
        ),
        created_at=tender.created_at,
        updated_at=tender.updated_at,
    )


def tender_document_ids(tender: Tender) -> list[UUID]:
    return [document.id for document in getattr(tender, "documents", [])]


def _read_tender_status(value: str | None) -> TenderStatus:
    normalized = (value or "").strip().lower()
    try:
        return TenderStatus(normalized)
    except ValueError:
        return LEGACY_TENDER_STATUS_MAP.get(normalized, TenderStatus.new)
