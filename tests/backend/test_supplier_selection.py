from datetime import datetime
from uuid import uuid4

from app.schemas.supplier import ContactRead, SupplierRead
from app.schemas.supplier_selection import SupplierRFQCandidateRequest
from app.services.supplier_selection import build_candidate


def _supplier(
    name: str,
    status: str = "active",
    preferred: bool = False,
    email: str | None = "estimating@example.com",
) -> SupplierRead:
    return SupplierRead(
        id=uuid4(),
        name=name,
        category="Asphalt",
        service_area="Lower Mainland",
        website=None,
        notes=None,
        metadata={"status": status, "preferred": preferred},
        contacts=[
            ContactRead(
                id=uuid4(),
                first_name="Estimating",
                last_name=None,
                email=email,
                phone=None,
                role="Estimating",
            )
        ],
        created_at=datetime(2026, 7, 1),
        updated_at=datetime(2026, 7, 1),
    )


def test_build_candidate_marks_preferred_supplier() -> None:
    payload = SupplierRFQCandidateRequest(category="Asphalt", service_area="Lower Mainland")
    candidate = build_candidate(_supplier("Superior Paving", preferred=True), payload)

    assert candidate is not None
    assert candidate.preferred is True
    assert candidate.selected_email == "estimating@example.com"
    assert "Preferred supplier" in candidate.reasons
    assert "Category match" in candidate.reasons
    assert "Service area match" in candidate.reasons


def test_build_candidate_excludes_bounced_supplier() -> None:
    payload = SupplierRFQCandidateRequest(category="Asphalt")
    candidate = build_candidate(_supplier("Bad Email Paving", status="bounced"), payload)

    assert candidate is None


def test_build_candidate_excludes_no_account_by_default() -> None:
    payload = SupplierRFQCandidateRequest(category="Asphalt")
    candidate = build_candidate(_supplier("Account Only Supplier", status="no_account"), payload)

    assert candidate is None


def test_build_candidate_can_include_no_account_with_warning() -> None:
    payload = SupplierRFQCandidateRequest(category="Asphalt", include_no_account=True)
    candidate = build_candidate(_supplier("Account Only Supplier", status="no_account"), payload)

    assert candidate is not None
    assert "Supplier may require an account" in candidate.warnings


def test_build_candidate_warns_when_email_missing() -> None:
    payload = SupplierRFQCandidateRequest(category="Asphalt")
    candidate = build_candidate(_supplier("No Email Supplier", email=None), payload)

    assert candidate is not None
    assert candidate.selected_email is None
    assert "No email available" in candidate.warnings
