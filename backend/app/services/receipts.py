import csv
import io
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.equipment import Equipment
from app.models.finance import (
    CompanyCard, FinancialEntry, Receipt, ReceiptAlias, ReceiptAuditEvent, ReceiptLineItem,
)
from app.models.media import MediaAsset, MediaRecordLink
from app.models.project import Project
from app.models.supplier import Supplier
from app.schemas.receipt import (
    ReceiptAction, ReceiptCreate, ReceiptLineItemInput, ReceiptLineItemRead, ReceiptList,
    ReceiptRead, ReceiptUpdate,
)
from app.services.auth import AuthenticatedUser
from app.services.media_access import can_access_asset

MANAGEMENT_ROLES = {"admin", "operations_manager"}
ROUNDING_TOLERANCE = Decimal("0.02")
MIN_CONFIDENCE = 0.70
CATEGORIES = {
    "fuel": ("fuel", "diesel", "gasoline", "def", "pump"),
    "tools": ("tool", "drill", "blade", "saw", "bit"),
    "ppe": ("ppe", "glove", "hard hat", "vest", "safety glass", "respirator"),
    "materials": ("pipe", "gravel", "concrete", "asphalt", "lumber", "fitting"),
    "equipment_parts_service": ("filter", "hydraulic", "bearing", "repair", "service", "part"),
    "rentals": ("rental", "rent "),
    "meals_travel": ("meal", "hotel", "parking", "flight", "restaurant"),
    "office_admin": ("office", "paper", "printer", "software", "subscription"),
}
BLOCKING_FLAGS = {"restricted_purchase", "unusual_purchase", "uncertain_purchase"}
REQUIRED_CONFIDENCE_FIELDS = {"vendor_name", "receipt_date", "subtotal", "total"}


def create_receipt(db: Session, payload: ReceiptCreate, user: AuthenticatedUser) -> ReceiptRead:
    assets = _assets(db, payload.media_asset_ids, user)
    receipt = Receipt(
        **_receipt_values(payload),
        submitter_id=user.id,
        submitter_email=user.email,
        image_hash=_image_hash(db, assets),
    )
    _apply_vendor_and_card_matches(db, receipt)
    db.add(receipt)
    db.flush()
    _replace_lines(db, receipt, payload.line_items)
    duplicate = _find_duplicate(db, receipt)
    if duplicate:
        receipt.duplicate_of_id = duplicate.id
        receipt.flags_json = sorted(set(receipt.flags_json + ["possible_duplicate"]))
    for asset in assets:
        db.add(MediaRecordLink(asset_id=asset.id, record_type="receipt", record_id=receipt.id))
    _audit(db, receipt, "extraction_created", user, to_status=receipt.status, changes={"image_count": len(assets)})
    db.commit()
    return get_receipt(db, receipt.id, user)


def list_receipts(db: Session, user: AuthenticatedUser, receipt_status: str | None = None) -> ReceiptList:
    statement = select(Receipt).order_by(Receipt.created_at.desc())
    if user.role not in MANAGEMENT_ROLES:
        statement = statement.where(Receipt.submitter_id == user.id)
    if receipt_status:
        statement = statement.where(Receipt.status == receipt_status)
    items = [_to_read(db, item) for item in db.scalars(statement).all()]
    return ReceiptList(items=items, total=len(items))


def get_receipt(db: Session, receipt_id: UUID, user: AuthenticatedUser) -> ReceiptRead:
    return _to_read(db, _require_receipt(db, receipt_id, user))


def update_receipt(db: Session, receipt_id: UUID, payload: ReceiptUpdate, user: AuthenticatedUser) -> ReceiptRead:
    receipt = _require_receipt(db, receipt_id, user)
    if receipt.status not in {"draft_extraction", "needs_review"}:
        raise HTTPException(status_code=409, detail="Approved, exported, reconciled, and void receipts cannot be edited.")
    if payload.version != receipt.version:
        raise HTTPException(status_code=409, detail="Receipt changed since it was loaded. Refresh before correcting it.")
    if payload.media_asset_ids is not None:
        supplied = set(payload.media_asset_ids)
        if supplied != set(UUID(value) for value in receipt.media_asset_ids):
            raise HTTPException(status_code=409, detail="Original receipt images are immutable; add an edited media version instead.")
    existing_flags = set(receipt.flags_json or [])
    requested_flags = set(payload.flags)
    if payload.duplicate_resolution or BLOCKING_FLAGS.intersection(existing_flags - requested_flags):
        _require_management(user)
    before = _snapshot(receipt, db)
    values = _receipt_values(payload)
    values.pop("media_asset_ids", None)
    for key, value in values.items():
        setattr(receipt, key, value)
    if payload.create_vendor:
        _require_management(user)
        if not receipt.vendor_name:
            raise HTTPException(status_code=422, detail="Vendor name is required before creating a controlled vendor record.")
        supplier = Supplier(name=receipt.vendor_name, category="receipt_vendor", metadata_json={"created_from_receipt": str(receipt.id)})
        db.add(supplier)
        db.flush()
        receipt.vendor_id = supplier.id
    elif payload.vendor_id:
        _require_management(user)
        supplier = db.get(Supplier, payload.vendor_id)
        if supplier is None:
            raise HTTPException(status_code=404, detail="Vendor record not found.")
        receipt.vendor_id = supplier.id
        receipt.vendor_name = supplier.name
    _apply_vendor_and_card_matches(db, receipt)
    _replace_lines(db, receipt, payload.line_items)
    receipt.version += 1
    duplicate = _find_duplicate(db, receipt)
    receipt.duplicate_of_id = duplicate.id if duplicate and payload.duplicate_resolution != "not_duplicate" else None
    if duplicate and payload.duplicate_resolution != "not_duplicate":
        receipt.flags_json = sorted(set(receipt.flags_json + ["possible_duplicate"]))
    else:
        receipt.flags_json = [flag for flag in receipt.flags_json if flag != "possible_duplicate"]
        if duplicate and payload.duplicate_resolution == "not_duplicate":
            receipt.flags_json = sorted(set(receipt.flags_json + ["duplicate_reviewed_not_duplicate"]))
    _audit(db, receipt, "correction_saved", user, reason=payload.correction_reason, changes=_diff(before, _snapshot(receipt, db)))
    db.commit()
    return get_receipt(db, receipt.id, user)


def submit_receipt(db: Session, receipt_id: UUID, action: ReceiptAction, user: AuthenticatedUser) -> ReceiptRead:
    receipt = _require_receipt(db, receipt_id, user)
    _check_version(receipt, action.version)
    if receipt.status != "draft_extraction":
        raise HTTPException(status_code=409, detail="Only draft extractions can be submitted for review.")
    previous = receipt.status
    receipt.status = "needs_review"
    receipt.version += 1
    _audit(db, receipt, "submitted_for_review", user, from_status=previous, to_status=receipt.status, reason=action.reason)
    db.commit()
    return get_receipt(db, receipt.id, user)


def approve_receipt(db: Session, receipt_id: UUID, action: ReceiptAction, user: AuthenticatedUser) -> ReceiptRead:
    _require_management(user)
    receipt = _require_receipt_for_update(db, receipt_id, user)
    _check_version(receipt, action.version)
    if receipt.status != "needs_review":
        raise HTTPException(status_code=409, detail="Only receipts awaiting review can be approved.")
    blockers = _approval_blockers(db, receipt)
    if blockers:
        raise HTTPException(status_code=422, detail={"message": "Receipt approval is blocked.", "blockers": blockers})
    previous = receipt.status
    receipt.status = "approved"
    receipt.approved_by = user.email
    receipt.approved_at = datetime.now(UTC)
    receipt.version += 1
    _learn_aliases(db, receipt, user)
    _audit(db, receipt, "approved", user, from_status=previous, to_status=receipt.status, reason=action.reason)
    db.commit()
    return get_receipt(db, receipt.id, user)


def export_receipt(db: Session, receipt_id: UUID, action: ReceiptAction, user: AuthenticatedUser) -> str:
    _require_management(user)
    receipt = _require_receipt_for_update(db, receipt_id, user)
    _check_version(receipt, action.version)
    if receipt.exported_at is not None:
        raise HTTPException(status_code=409, detail="Receipt was already exported; duplicate export is blocked.")
    if receipt.status != "approved" or not receipt.approved_by:
        raise HTTPException(status_code=409, detail="An authorized human must approve this receipt before export.")
    lines = _lines(db, receipt.id)
    rows = [["Date", "Reference", "Vendor", "Project ID", "Equipment ID", "Cost Code", "Overhead", "Category", "Description", "Amount CAD", "Tax CAD", "Treatment", "Receipt ID"]]
    for line in lines:
        rows.append([
            receipt.receipt_date.isoformat(), receipt.reference or "", receipt.vendor_name or "",
            str(line.project_id or ""), str(line.equipment_id or ""), line.cost_code or "", line.overhead_category or "",
            line.category, line.normalized_description or line.description, f"{float(line.line_total):.2f}",
            f"{float(line.tax):.2f}", line.treatment, str(receipt.id),
        ])
        if line.project_id:
            db.add(FinancialEntry(
                project_id=line.project_id, cost_code=line.cost_code, entry_type="actual",
                category=_financial_category(line.category), amount=line.line_total,
                entry_date=receipt.receipt_date, vendor_name=receipt.vendor_name, reference=receipt.reference,
                description=line.normalized_description or line.description, source_type="approved_receipt",
                source_id=receipt.id, status="posted", metadata_json={"receipt_id": str(receipt.id), "line_item_id": str(line.id)},
                created_by=user.email,
            ))
    previous = receipt.status
    receipt.status = "exported"
    receipt.exported_by = user.email
    receipt.exported_at = datetime.now(UTC)
    receipt.version += 1
    _audit(db, receipt, "exported_and_posted", user, from_status=previous, to_status=receipt.status, reason=action.reason, changes={"rows": len(lines)})
    db.commit()
    buffer = io.StringIO()
    csv.writer(buffer).writerows(rows)
    return buffer.getvalue()


def reconcile_receipt(db: Session, receipt_id: UUID, action: ReceiptAction, user: AuthenticatedUser) -> ReceiptRead:
    _require_management(user)
    receipt = _require_receipt(db, receipt_id, user)
    _check_version(receipt, action.version)
    if receipt.status != "exported":
        raise HTTPException(status_code=409, detail="Only an exported receipt can be reconciled.")
    previous = receipt.status
    receipt.status = "reconciled"
    receipt.version += 1
    _audit(db, receipt, "reconciled", user, from_status=previous, to_status=receipt.status, reason=action.reason)
    db.commit()
    return get_receipt(db, receipt.id, user)


def void_receipt(db: Session, receipt_id: UUID, action: ReceiptAction, user: AuthenticatedUser) -> ReceiptRead:
    _require_management(user)
    receipt = _require_receipt(db, receipt_id, user)
    _check_version(receipt, action.version)
    if receipt.status in {"exported", "reconciled", "void"}:
        raise HTTPException(status_code=409, detail="Exported or reconciled receipts require an accounting reversal and cannot be voided here.")
    previous = receipt.status
    receipt.status = "void"
    receipt.voided_by = user.email
    receipt.voided_at = datetime.now(UTC)
    receipt.version += 1
    _audit(db, receipt, "voided", user, from_status=previous, to_status=receipt.status, reason=action.reason)
    db.commit()
    return get_receipt(db, receipt.id, user)


def _assets(db: Session, asset_ids: list[UUID], user: AuthenticatedUser) -> list[MediaAsset]:
    if len(set(asset_ids)) != len(asset_ids):
        raise HTTPException(status_code=422, detail="Receipt pages must be unique.")
    assets = []
    for asset_id in asset_ids:
        asset = db.get(MediaAsset, asset_id)
        if asset is None or not can_access_asset(asset, user):
            raise HTTPException(status_code=404, detail="Receipt image not found.")
        if asset.category != "receipt" or not asset.controlled:
            raise HTTPException(status_code=422, detail="Only controlled receipt media can be submitted.")
        assets.append(asset)
    return assets


def _image_hash(db: Session, assets: list[MediaAsset]) -> str:
    hashes = []
    for asset in assets:
        document = db.get(Document, asset.original_document_id)
        digest = (document.metadata_json or {}).get("sha256_hash") if document else None
        if not digest:
            raise HTTPException(status_code=409, detail="Receipt image integrity hash is unavailable.")
        hashes.append(digest)
    return sha256("|".join(sorted(hashes)).encode()).hexdigest()


def _receipt_values(payload: ReceiptCreate | ReceiptUpdate) -> dict:
    values = payload.model_dump(exclude={"line_items", "correction_reason", "vendor_id", "create_vendor", "duplicate_resolution", "version"})
    if values.get("media_asset_ids") is not None:
        values["media_asset_ids"] = [str(value) for value in values["media_asset_ids"]]
    values["confidence_json"] = values.pop("confidence")
    values["source_regions_json"] = {key: value for key, value in values.pop("source_regions").items()}
    values["flags_json"] = values.pop("flags")
    return values


def _replace_lines(db: Session, receipt: Receipt, items: list[ReceiptLineItemInput]) -> None:
    db.execute(delete(ReceiptLineItem).where(ReceiptLineItem.receipt_id == receipt.id))
    db.flush()
    for position, item in enumerate(items, start=1):
        values = item.model_dump()
        values["source_region_json"] = values.pop("source_region") or {}
        values["flags_json"] = values.pop("flags")
        _validate_line_references(db, item)
        if item.category == "uncategorized":
            values["category"] = _suggest_category(item.description)
        alias = None
        if receipt.vendor_id:
            alias = db.scalar(select(ReceiptAlias).where(ReceiptAlias.vendor_id == receipt.vendor_id, func.lower(ReceiptAlias.raw_value) == item.description.strip().lower()))
        if alias:
            values.update(normalized_description=alias.normalized_value, category=alias.category, cost_code=item.cost_code or alias.cost_code, confidence=max(item.confidence, 0.9))
        db.add(ReceiptLineItem(receipt_id=receipt.id, position=position, **values))


def _validate_line_references(db: Session, item: ReceiptLineItemInput) -> None:
    if item.project_id and db.get(Project, item.project_id) is None:
        raise HTTPException(status_code=404, detail="Line-item project not found.")
    if item.equipment_id and db.get(Equipment, item.equipment_id) is None:
        raise HTTPException(status_code=404, detail="Line-item equipment not found.")


def _apply_vendor_and_card_matches(db: Session, receipt: Receipt) -> None:
    receipt.vendor_id = None
    if receipt.vendor_name:
        supplier = db.scalar(select(Supplier).where(func.lower(Supplier.name) == receipt.vendor_name.strip().lower()))
        if supplier:
            receipt.vendor_id = supplier.id
            receipt.vendor_name = supplier.name
    receipt.company_card_id = None
    if receipt.card_brand and receipt.card_last_four:
        cards = list(db.scalars(select(CompanyCard).where(
            func.lower(CompanyCard.brand) == receipt.card_brand.strip().lower(),
            CompanyCard.last_four == receipt.card_last_four,
            CompanyCard.is_authorized.is_(True),
        )).all())
        if len(cards) == 1:
            receipt.company_card_id = cards[0].id
            receipt.employee_email = receipt.employee_email or cards[0].holder_email
        elif len(cards) > 1:
            receipt.flags_json = sorted(set(receipt.flags_json + ["ambiguous_company_card"]))


def _find_duplicate(db: Session, receipt: Receipt) -> Receipt | None:
    candidates = list(db.scalars(select(Receipt).where(Receipt.id != receipt.id, Receipt.status != "void", or_(
        Receipt.image_hash == receipt.image_hash,
        and_(
            func.lower(Receipt.vendor_name) == (receipt.vendor_name or "").lower(),
            Receipt.receipt_date == receipt.receipt_date,
            Receipt.total == receipt.total,
        ),
        and_(Receipt.reference.is_not(None), Receipt.reference == receipt.reference, func.lower(Receipt.vendor_name) == (receipt.vendor_name or "").lower()),
    )).order_by(Receipt.created_at)).all())
    return candidates[0] if candidates else None


def _approval_blockers(db: Session, receipt: Receipt) -> list[str]:
    blockers = []
    for field in ("vendor_name", "receipt_date", "subtotal", "total"):
        if getattr(receipt, field) is None:
            blockers.append(f"Missing required field: {field.replace('_', ' ')}.")
    for field in REQUIRED_CONFIDENCE_FIELDS:
        if float((receipt.confidence_json or {}).get(field, 0)) < MIN_CONFIDENCE:
            blockers.append(f"Low-confidence field requires correction: {field.replace('_', ' ')}.")
    difference = _reconciliation_difference(receipt)
    if difference is None or abs(difference) > ROUNDING_TOLERANCE:
        blockers.append(f"Receipt total is out of balance by {float(difference or 0):.2f} CAD.")
    if receipt.duplicate_of_id:
        blockers.append("Possible duplicate receipt must be resolved before approval.")
    if receipt.treatment == "company_card" and receipt.company_card_id is None:
        blockers.append("Company-card treatment requires one authorized brand/last-four match.")
    if receipt.treatment == "needs_review":
        blockers.append("Payment treatment must be confirmed.")
    if BLOCKING_FLAGS.intersection(receipt.flags_json or []):
        blockers.append("Restricted, unusual, or uncertain purchase flag requires resolution.")
    lines = _lines(db, receipt.id)
    if not lines:
        blockers.append("At least one line item is required.")
    elif receipt.subtotal is not None:
        line_subtotal = sum((Decimal(str(line.line_total)) for line in lines), Decimal("0"))
        if abs(line_subtotal - Decimal(str(receipt.subtotal))) > ROUNDING_TOLERANCE:
            blockers.append("Line-item totals do not reconcile to the receipt subtotal.")
        line_tax = sum((Decimal(str(line.tax)) for line in lines), Decimal("0"))
        header_tax = Decimal(str(receipt.gst)) + Decimal(str(receipt.pst)) + Decimal(str(receipt.other_tax))
        if abs(line_tax - header_tax) > ROUNDING_TOLERANCE:
            blockers.append("Line-item taxes do not reconcile to the receipt tax total.")
    for line in lines:
        expected_line_total = Decimal(str(line.quantity)) * Decimal(str(line.unit_price))
        if abs(expected_line_total - Decimal(str(line.line_total))) > ROUNDING_TOLERANCE:
            blockers.append(f"Line {line.position} total does not match quantity × unit price.")
        prefix = f"Line {line.position}"
        if float(line.confidence) < MIN_CONFIDENCE:
            blockers.append(f"{prefix} has low confidence.")
        if line.category == "uncategorized":
            blockers.append(f"{prefix} needs a controlled purchase category.")
        if line.treatment == "needs_review":
            blockers.append(f"{prefix} payment treatment is unconfirmed.")
        if not ((line.project_id and line.cost_code) or line.overhead_category):
            blockers.append(f"{prefix} needs project and cost code, or an approved overhead category.")
        if BLOCKING_FLAGS.intersection(line.flags_json or []):
            blockers.append(f"{prefix} has a restricted, unusual, or uncertain purchase flag.")
    return blockers


def _reconciliation_difference(receipt: Receipt) -> Decimal | None:
    if receipt.subtotal is None or receipt.total is None:
        return None
    calculated = Decimal(str(receipt.subtotal)) - Decimal(str(receipt.discounts)) + Decimal(str(receipt.gst)) + Decimal(str(receipt.pst)) + Decimal(str(receipt.other_tax)) + Decimal(str(receipt.tip))
    return (calculated - Decimal(str(receipt.total))).quantize(Decimal("0.01"))


def _to_read(db: Session, receipt: Receipt) -> ReceiptRead:
    difference = _reconciliation_difference(receipt)
    lines = [ReceiptLineItemRead(
        id=line.id, position=line.position, description=line.description,
        normalized_description=line.normalized_description, quantity=float(line.quantity), unit_price=float(line.unit_price),
        tax=float(line.tax), line_total=float(line.line_total), category=line.category, project_id=line.project_id,
        equipment_id=line.equipment_id, cost_code=line.cost_code, overhead_category=line.overhead_category,
        treatment=line.treatment, confidence=float(line.confidence), source_region=line.source_region_json or None,
        flags=line.flags_json or [],
    ) for line in _lines(db, receipt.id)]
    audits = list(db.scalars(select(ReceiptAuditEvent).where(ReceiptAuditEvent.receipt_id == receipt.id).order_by(ReceiptAuditEvent.created_at.desc())).all())
    return ReceiptRead(
        id=receipt.id, status=receipt.status, submitter_email=receipt.submitter_email,
        media_asset_ids=[UUID(value) for value in receipt.media_asset_ids], image_hash=receipt.image_hash,
        vendor_id=receipt.vendor_id, vendor_name=receipt.vendor_name, vendor_address=receipt.vendor_address,
        reference=receipt.reference, receipt_date=receipt.receipt_date, receipt_time=receipt.receipt_time,
        currency=receipt.currency, subtotal=_float(receipt.subtotal), discounts=float(receipt.discounts),
        gst=float(receipt.gst), pst=float(receipt.pst), other_tax=float(receipt.other_tax), tip=float(receipt.tip),
        total=_float(receipt.total), payment_method=receipt.payment_method, card_brand=receipt.card_brand,
        card_last_four=receipt.card_last_four, company_card_id=receipt.company_card_id,
        employee_email=receipt.employee_email, treatment=receipt.treatment, confidence=receipt.confidence_json or {},
        source_regions=receipt.source_regions_json or {}, flags=receipt.flags_json or [], duplicate_of_id=receipt.duplicate_of_id,
        approved_by=receipt.approved_by, approved_at=receipt.approved_at, exported_by=receipt.exported_by,
        exported_at=receipt.exported_at, version=receipt.version,
        reconciliation_difference=float(difference) if difference is not None else None,
        is_balanced=difference is not None and abs(difference) <= ROUNDING_TOLERANCE,
        approval_blockers=_approval_blockers(db, receipt), line_items=lines, audit_history=audits,
        created_at=receipt.created_at, updated_at=receipt.updated_at,
    )


def _require_receipt_for_update(db: Session, receipt_id: UUID, user: AuthenticatedUser) -> Receipt:
    receipt = db.scalar(select(Receipt).where(Receipt.id == receipt_id).with_for_update())
    if receipt is None or (user.role not in MANAGEMENT_ROLES and receipt.submitter_id != user.id):
        raise HTTPException(status_code=404, detail="Receipt not found.")
    return receipt


def _require_receipt(db: Session, receipt_id: UUID, user: AuthenticatedUser) -> Receipt:
    receipt = db.get(Receipt, receipt_id)
    if receipt is None or (user.role not in MANAGEMENT_ROLES and receipt.submitter_id != user.id):
        raise HTTPException(status_code=404, detail="Receipt not found.")
    return receipt


def _require_management(user: AuthenticatedUser) -> None:
    if user.role not in MANAGEMENT_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authorized financial reviewer access is required.")


def _check_version(receipt: Receipt, version: int) -> None:
    if receipt.version != version:
        raise HTTPException(status_code=409, detail="Receipt changed since it was loaded. Refresh before continuing.")


def _lines(db: Session, receipt_id: UUID) -> list[ReceiptLineItem]:
    return list(db.scalars(select(ReceiptLineItem).where(ReceiptLineItem.receipt_id == receipt_id).order_by(ReceiptLineItem.position)).all())


def _audit(db: Session, receipt: Receipt, action: str, user: AuthenticatedUser, *, from_status: str | None = None, to_status: str | None = None, reason: str | None = None, changes: dict | None = None) -> None:
    db.add(ReceiptAuditEvent(receipt_id=receipt.id, action=action, actor_email=user.email, from_status=from_status, to_status=to_status, reason=reason, changes_json=changes or {}))


def _snapshot(receipt: Receipt, db: Session) -> dict:
    return {
        "vendor_id": str(receipt.vendor_id) if receipt.vendor_id else None, "vendor_name": receipt.vendor_name,
        "reference": receipt.reference, "receipt_date": str(receipt.receipt_date), "subtotal": _float(receipt.subtotal),
        "discounts": float(receipt.discounts), "gst": float(receipt.gst), "pst": float(receipt.pst),
        "other_tax": float(receipt.other_tax), "tip": float(receipt.tip), "total": _float(receipt.total),
        "treatment": receipt.treatment, "line_items": [{"position": line.position, "description": line.description,
        "category": line.category, "project_id": str(line.project_id) if line.project_id else None,
        "cost_code": line.cost_code, "overhead_category": line.overhead_category} for line in _lines(db, receipt.id)],
    }


def _diff(before: dict, after: dict) -> dict:
    return {key: {"from": before.get(key), "to": value} for key, value in after.items() if before.get(key) != value}


def _learn_aliases(db: Session, receipt: Receipt, user: AuthenticatedUser) -> None:
    if not receipt.vendor_id:
        return
    for line in _lines(db, receipt.id):
        normalized = (line.normalized_description or "").strip()
        raw = line.description.strip()
        if normalized and normalized.lower() != raw.lower():
            existing = db.scalar(select(ReceiptAlias).where(ReceiptAlias.vendor_id == receipt.vendor_id, func.lower(ReceiptAlias.raw_value) == raw.lower()))
            if existing:
                existing.normalized_value = normalized
                existing.category = line.category
                existing.cost_code = line.cost_code
                existing.approved_by = user.email
            else:
                db.add(ReceiptAlias(vendor_id=receipt.vendor_id, raw_value=raw, normalized_value=normalized, category=line.category, cost_code=line.cost_code, approved_by=user.email))


def _suggest_category(description: str) -> str:
    lowered = description.lower()
    for category, keywords in CATEGORIES.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return "uncategorized"


def _financial_category(category: str) -> str:
    return {"fuel": "fuel", "materials": "material", "equipment_parts_service": "equipment", "rentals": "rental"}.get(category, "overhead" if category in {"meals_travel", "office_admin"} else "other")


def _float(value) -> float | None:
    return float(value) if value is not None else None
