from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.supplier import SupplierRead
from app.schemas.supplier_selection import SupplierRFQCandidate, SupplierRFQCandidateRequest
from app.services import suppliers

EXCLUDED_STATUSES = {"bounced", "do not use", "do_not_use", "archived"}
NO_ACCOUNT_STATUSES = {"no account", "no_account"}
NEEDS_VERIFICATION_STATUSES = {"needs verification", "needs_verification"}


def select_rfq_candidates(db: Session, payload: SupplierRFQCandidateRequest) -> list[SupplierRFQCandidate]:
    supplier_items = suppliers.list_suppliers(
        db,
        category=payload.category,
        service_area=payload.service_area,
    )
    candidates = [
        candidate
        for supplier in supplier_items
        if (candidate := build_candidate(supplier, payload)) is not None
    ]
    candidates.sort(key=_candidate_sort_key)
    return candidates[: payload.limit]


def build_candidate(
    supplier: SupplierRead,
    payload: SupplierRFQCandidateRequest,
) -> SupplierRFQCandidate | None:
    metadata = supplier.metadata or {}
    status = str(metadata.get("status") or "active").strip().lower()
    preferred = bool(metadata.get("preferred", False)) or status == "preferred"
    reasons: list[str] = []
    warnings: list[str] = []

    if status in EXCLUDED_STATUSES:
        return None
    if status in NO_ACCOUNT_STATUSES and not payload.include_no_account:
        return None
    if status in NEEDS_VERIFICATION_STATUSES and not payload.include_needs_verification:
        return None

    selected_email = _select_email(supplier)
    if selected_email is None:
        warnings.append("No email available")
    else:
        reasons.append("Email available")

    if preferred:
        reasons.append("Preferred supplier")
    if supplier.category == payload.category:
        reasons.append("Category match")
    if payload.service_area and supplier.service_area == payload.service_area:
        reasons.append("Service area match")
    if status in NEEDS_VERIFICATION_STATUSES:
        warnings.append("Contact needs verification")
    if status in NO_ACCOUNT_STATUSES:
        warnings.append("Supplier may require an account")

    return SupplierRFQCandidate(
        supplier=supplier,
        selected_email=selected_email,
        preferred=preferred,
        status=status,
        reasons=reasons,
        warnings=warnings,
    )


def _select_email(supplier: SupplierRead) -> str | None:
    for contact in supplier.contacts:
        if contact.email and contact.role and "estim" in contact.role.lower():
            return contact.email
    for contact in supplier.contacts:
        if contact.email:
            return contact.email
    metadata_email = supplier.metadata.get("email") if supplier.metadata else None
    return str(metadata_email) if metadata_email else None


def _candidate_sort_key(candidate: SupplierRFQCandidate) -> tuple[int, int, str]:
    has_email_rank = 0 if candidate.selected_email else 1
    preferred_rank = 0 if candidate.preferred else 1
    return (preferred_rank, has_email_rank, candidate.supplier.name.lower())
