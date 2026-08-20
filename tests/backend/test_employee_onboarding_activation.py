from collections.abc import Generator
from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.employee_onboarding import EmployeeOnboarding, EmployeeOnboardingAudit, WorkerOrientation
from app.models.user import Employee, UserAccount
from app.schemas.employee_onboarding import REQUIRED_ORIENTATION_TOPIC_CODES
from app.services.auth import hash_password, verify_password
from app.services.employee_onboarding import portal_role_for_position


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
            legal_last_name="Operator",
            preferred_name="Alex",
            personal_email="ALEX.OPERATOR@EXAMPLE.COM",
            category="field_staff",
            position="equipment_operator",
            employment_type="full_time",
            start_date=date(2026, 8, 20),
            status="approved",
            completion_percent=100,
            completed_items=[],
            missing_items=[],
        )
        db.add(onboarding)
        db.flush()
        topics = [
            {
                "code": code,
                "applicability": "applicable",
                "evidence": f"Completed: {code}",
                "not_applicable_basis": None,
            }
            for code in REQUIRED_ORIENTATION_TOPIC_CODES
        ]
        for scope in ("company", "site"):
            db.add(
                WorkerOrientation(
                    onboarding_id=onboarding.id,
                    project_id=None,
                    scope=scope,
                    site_name="Test Site" if scope == "site" else None,
                    trigger="new_hire" if scope == "company" else "new_site",
                    orientation_date=date(2026, 8, 20),
                    instructor_name="Instructor",
                    supervisor_name="Supervisor",
                    document_version="2026-08",
                    topics=topics,
                    competency_result="passed",
                    ppe_verified=True,
                    qualifications_verified=True,
                    worker_acknowledged=True,
                    worker_acknowledged_at=datetime.now(UTC),
                    supporting_document_ids=[],
                    created_by="admin@ironhousecontracting.com",
                )
            )
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


def test_activation_creates_position_scoped_credentials_once() -> None:
    client, testing_session, onboarding_id = _client()

    response = client.post(f"/api/v1/employee-onboarding/{onboarding_id}/activate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["username"] == "alex.operator@example.com"
    assert payload["portal_role"] == "operator"
    assert len(payload["temporary_password"]) >= 12
    assert payload["onboarding"]["status"] == "active"

    with testing_session() as db:
        employee = db.query(Employee).filter_by(email="alex.operator@example.com").one()
        account = db.query(UserAccount).filter_by(email="alex.operator@example.com").one()
        audit = db.query(EmployeeOnboardingAudit).filter_by(action="activated").one()
        assert employee.portal_role == "operator"
        assert account.role == "viewer"
        assert account.password_reset_required is True
        assert verify_password(payload["temporary_password"], account.password_hash)
        assert "temporary_password" not in audit.metadata_json
        assert "password" not in audit.metadata_json

    repeated = client.post(f"/api/v1/employee-onboarding/{onboarding_id}/activate")
    assert repeated.status_code == 409
    assert "approved" in repeated.json()["detail"].lower()

    listed = client.get("/api/v1/employee-onboarding")
    assert listed.status_code == 200
    assert "temporary_password" not in listed.text

    client.post("/api/v1/auth/logout")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": payload["username"], "password": payload["temporary_password"]},
    )
    assert login.status_code == 200
    assert login.json()["user"]["password_reset_required"] is True
    blocked = client.get("/api/v1/field-operations/bootstrap")
    assert blocked.status_code == 403
    assert "temporary password" in blocked.json()["detail"]
    changed = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": payload["temporary_password"],
            "new_password": "employee-selected-password-2026",
        },
    )
    assert changed.status_code == 200
    bootstrap = client.get("/api/v1/field-operations/bootstrap")
    assert bootstrap.status_code == 200
    assert bootstrap.json()["employees"][0]["portal_role"] == "operator"


def test_activation_rejects_an_existing_portal_identity_without_overwriting() -> None:
    client, testing_session, onboarding_id = _client()
    with testing_session() as db:
        db.add(
            UserAccount(
                email="alex.operator@example.com",
                display_name="Existing Account",
                role="viewer",
                password_hash=hash_password("existing-account-password"),
                is_active=True,
                session_version=4,
            )
        )
        db.commit()

    response = client.post(f"/api/v1/employee-onboarding/{onboarding_id}/activate")

    assert response.status_code == 409
    assert "administrator review" in response.json()["detail"]
    with testing_session() as db:
        assert db.query(Employee).filter_by(email="alex.operator@example.com").count() == 0
        account = db.query(UserAccount).filter_by(email="alex.operator@example.com").one()
        assert account.display_name == "Existing Account"
        assert account.session_version == 4


def test_executive_titles_do_not_auto_escalate_portal_access() -> None:
    assert portal_role_for_position("ceo") == "employee"
    assert portal_role_for_position("president") == "employee"
    assert portal_role_for_position("cfo") == "employee"
