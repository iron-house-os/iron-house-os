from collections.abc import Generator
from datetime import date
from urllib.parse import urlparse
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.employee_onboarding import EmployeeOnboarding, EmployeeOnboardingAudit
from app.models.user import UserAccount
from app.services.auth import hash_password
from app.services.employee_onboarding import REQUIRED_ITEMS


def _client() -> tuple[TestClient, sessionmaker[Session], str]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with testing_session() as db:
        db.add(
            UserAccount(
                email="admin@ironhousecontracting.com",
                display_name="Staging Admin",
                role="admin",
                password_hash=hash_password("correct-horse-battery-staple"),
                is_active=True,
                session_version=1,
            )
        )
        onboarding = EmployeeOnboarding(
            legal_first_name="Alex",
            legal_last_name="Worker",
            personal_email="alex.worker@example.com",
            category="field_staff",
            position="labourer",
            employment_type="full_time",
            start_date=date(2026, 8, 20),
            status="draft",
            completion_percent=0,
            completed_items=[],
            missing_items=REQUIRED_ITEMS.copy(),
        )
        db.add(onboarding)
        db.commit()
        onboarding_id = str(onboarding.id)

    app = create_app()

    def override_db() -> Generator[Session, None, None]:
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@ironhousecontracting.com",
            "password": "correct-horse-battery-staple",
        },
    )
    return client, testing_session, onboarding_id


def _token(invite_url: str) -> str:
    return urlparse(invite_url).path.rsplit("/", 1)[-1]


def _packet() -> dict:
    return {
        "personal_information": {
            "preferred_name": "Alex",
            "mobile_phone": "250-555-0114",
            "date_of_birth": "1990-01-02",
        },
        "address": {
            "street_address": "100 Main Street",
            "unit": None,
            "city": "Dawson Creek",
            "province": "BC",
            "postal_code": "V1G 1A1",
            "country": "Canada",
        },
        "emergency_contact": {
            "full_name": "Jordan Worker",
            "relationship": "Partner",
            "primary_phone": "250-555-0188",
            "alternate_phone": None,
        },
        "payroll": {
            "payment_method": "direct_deposit",
            "account_holder_name": "Alex Worker",
            "institution_number": "001",
            "transit_number": "12345",
            "account_number": "1234567",
            "direct_deposit_authorized": True,
        },
        "tax_forms": {
            "form_year": 2026,
            "social_insurance_number": "046454286",
            "country_of_permanent_residence": "Canada",
            "federal_claim_amounts": ["16452", *(["0"] * 11)],
            "bc_claim_amounts": ["13216", *(["0"] * 9)],
            "federal_more_than_one_employer": False,
            "federal_total_income_less_than_claim": False,
            "non_resident_world_income_90_percent_or_more": None,
            "additional_tax_per_payment": "0",
            "bc_more_than_one_employer": False,
            "bc_total_income_less_than_claim": False,
            "federal_certified": True,
            "bc_certified": True,
        },
        "employment_agreements": {
            "employment_terms_reviewed": True,
            "company_policies_reviewed": True,
            "privacy_notice_reviewed": True,
            "purchase_receipt_standard_reviewed": True,
            "questions_resolved": True,
        },
        "certifications": {
            "none_to_report": True,
            "certifications": [],
        },
        "ppe_requirements": {
            "site_ppe_required": True,
            "boot_size": "10",
            "glove_size": "L",
            "shirt_size": "L",
            "trouser_size": "34x32",
            "prescription_safety_glasses": False,
            "respirator_fit_test_required": False,
            "notes": None,
        },
    }


def test_employee_invitation_progress_submission_and_status_boundary() -> None:
    client, testing_session, onboarding_id = _client()
    invitation = client.post(f"/api/v1/employee-onboarding/{onboarding_id}/invite")
    assert invitation.status_code == 200
    token = _token(invitation.json()["invite_url"])
    client.post("/api/v1/auth/logout")

    opened = client.get(f"/api/v1/employee-onboarding/portal/{token}")
    assert opened.status_code == 200
    assert opened.json()["onboarding"]["status"] == "invitation_opened"
    assert opened.json()["packet"] == {
        "personal_information": None,
        "address": None,
        "emergency_contact": None,
        "payroll": None,
        "tax_forms": None,
        "employment_agreements": None,
        "certifications": None,
        "ppe_requirements": None,
        "signature_name": None,
        "signed_at": None,
    }

    partial_packet = _packet()
    partial_packet["emergency_contact"] = None
    partial_packet["payroll"] = None
    partial_packet["tax_forms"] = None
    partial_packet["employment_agreements"] = None
    partial_packet["certifications"] = None
    partial_packet["ppe_requirements"] = None
    progress = client.put(
        f"/api/v1/employee-onboarding/portal/{token}/progress",
        json={"packet": partial_packet},
    )
    assert progress.status_code == 200
    assert progress.json()["onboarding"]["completion_percent"] == 22

    incomplete = client.post(
        f"/api/v1/employee-onboarding/portal/{token}/submit",
        json={
            "packet": partial_packet,
            "acknowledgement": True,
            "signature_name": "Alex Worker",
        },
    )
    assert incomplete.status_code == 422

    submitted = client.post(
        f"/api/v1/employee-onboarding/portal/{token}/submit",
        json={
            "packet": _packet(),
            "acknowledgement": True,
            "signature_name": "Alex Worker",
        },
    )
    assert submitted.status_code == 200
    assert submitted.json()["onboarding"]["status"] == "submitted"
    assert submitted.json()["packet"]["signature_name"] == "Alex Worker"
    with testing_session() as db:
        stored = db.get(EmployeeOnboarding, UUID(onboarding_id))
        assert stored is not None
        assert stored.encrypted_portal_data
        assert "046454286" not in stored.encrypted_portal_data
        assert "1234567" not in stored.encrypted_portal_data

    late_change = client.put(
        f"/api/v1/employee-onboarding/portal/{token}/progress",
        json={"packet": _packet()},
    )
    assert late_change.status_code == 409

    client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@ironhousecontracting.com",
            "password": "correct-horse-battery-staple",
        },
    )
    listed = client.get("/api/v1/employee-onboarding")
    assert listed.status_code == 200
    assert "encrypted_portal_data" not in listed.text
    assert "046454286" not in listed.text
    reviewed = client.get(f"/api/v1/employee-onboarding/{onboarding_id}/packet")
    assert reviewed.status_code == 200
    assert reviewed.json()["tax_forms"]["social_insurance_number"] == "046454286"
    with testing_session() as db:
        actions = [item.action for item in db.query(EmployeeOnboardingAudit).all()]
        assert "restricted_packet_viewed" in actions
    assert client.post(f"/api/v1/employee-onboarding/{onboarding_id}/approve").status_code == 200
    assert client.get(f"/api/v1/employee-onboarding/portal/{token}").status_code == 404


def test_resend_invalidates_the_previous_invitation_token() -> None:
    client, _, onboarding_id = _client()
    first = client.post(f"/api/v1/employee-onboarding/{onboarding_id}/invite")
    second = client.post(f"/api/v1/employee-onboarding/{onboarding_id}/invite")
    first_token = _token(first.json()["invite_url"])
    second_token = _token(second.json()["invite_url"])
    client.post("/api/v1/auth/logout")

    assert first_token != second_token
    assert client.get(f"/api/v1/employee-onboarding/portal/{first_token}").status_code == 404
    assert client.get(f"/api/v1/employee-onboarding/portal/{second_token}").status_code == 200
