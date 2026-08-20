from collections.abc import Generator
from datetime import date
from urllib.parse import urlparse

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.employee_onboarding import EmployeeOnboarding
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


def test_employee_invitation_progress_submission_and_status_boundary() -> None:
    client, _, onboarding_id = _client()
    invitation = client.post(f"/api/v1/employee-onboarding/{onboarding_id}/invite")
    assert invitation.status_code == 200
    token = _token(invitation.json()["invite_url"])
    client.post("/api/v1/auth/logout")

    opened = client.get(f"/api/v1/employee-onboarding/portal/{token}")
    assert opened.status_code == 200
    assert opened.json()["status"] == "invitation_opened"

    progress = client.put(
        f"/api/v1/employee-onboarding/portal/{token}/progress",
        json={"completed_items": REQUIRED_ITEMS[:2]},
    )
    assert progress.status_code == 200
    assert progress.json()["completion_percent"] == 20

    incomplete = client.post(
        f"/api/v1/employee-onboarding/portal/{token}/submit",
        json={"completed_items": REQUIRED_ITEMS[:2], "acknowledgement": True},
    )
    assert incomplete.status_code == 422

    submitted = client.post(
        f"/api/v1/employee-onboarding/portal/{token}/submit",
        json={"completed_items": REQUIRED_ITEMS, "acknowledgement": True},
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"

    late_change = client.put(
        f"/api/v1/employee-onboarding/portal/{token}/progress",
        json={"completed_items": []},
    )
    assert late_change.status_code == 409

    client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@ironhousecontracting.com",
            "password": "correct-horse-battery-staple",
        },
    )
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
