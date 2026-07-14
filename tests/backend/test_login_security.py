from collections.abc import Generator
import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.user import LoginThrottle, UserAccount
from app.services.auth import hash_password
from app.services.document_audit import (
    clear_recent_document_audit_events,
    list_recent_document_audit_events,
)

ADMIN_EMAIL = "security-admin@ironhousecivil.com"
ADMIN_PASSWORD = "correct-horse-battery-staple"


def _client() -> tuple[TestClient, sessionmaker[Session]]:
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
                email=ADMIN_EMAIL,
                display_name="Security Administrator",
                role="admin",
                password_hash=hash_password(ADMIN_PASSWORD),
                is_active=True,
                session_version=1,
                password_reset_required=False,
            )
        )
        db.commit()

    app = create_app()

    def override_db() -> Generator[Session, None, None]:
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    clear_recent_document_audit_events()
    return TestClient(app), testing_session


def test_failed_logins_are_persistently_throttled_without_account_disclosure() -> None:
    client, testing_session = _client()

    for attempt in range(1, 6):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": "wrong-password"},
        )
        assert response.status_code == (429 if attempt == 5 else 401)

    locked_response = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert locked_response.status_code == 429
    assert int(locked_response.headers["retry-after"]) > 0

    unknown_response = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "wrong-password"},
    )
    assert unknown_response.status_code == 401
    assert unknown_response.json() == {"detail": "Email or password is incorrect."}

    with testing_session() as db:
        throttle = db.scalar(select(LoginThrottle).where(LoginThrottle.failed_attempts == 5))
        assert throttle is not None
        assert throttle.locked_until is not None

    events = list_recent_document_audit_events(action="login")
    rendered = json.dumps(events)
    assert "wrong-password" not in rendered
    assert ADMIN_EMAIL not in rendered
    assert any(event["outcome"] == "locked" for event in events)


def test_admin_recovery_forces_password_change_and_clears_lockout() -> None:
    client, testing_session = _client()
    assert client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    ).status_code == 200
    created = client.post(
        "/api/v1/users",
        json={
            "email": "recovering-estimator@ironhousecivil.com",
            "display_name": "Recovering Estimator",
            "role": "estimator",
            "password": "initial-password-2026",
        },
    )
    assert created.status_code == 201
    assert created.json()["password_reset_required"] is True
    account_id = created.json()["id"]

    for _ in range(5):
        client.post("/api/v1/auth/logout")
        client.post(
            "/api/v1/auth/login",
            json={"email": "recovering-estimator@ironhousecivil.com", "password": "wrong-password"},
        )

    client.cookies.clear()
    assert client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    ).status_code == 200
    recovery = client.post(
        f"/api/v1/users/{account_id}/reset-password",
        json={"password": "temporary-password-2026"},
        headers={"x-request-id": "build-211-recovery"},
    )
    assert recovery.status_code == 200
    assert recovery.json()["password_reset_required"] is True

    client.post("/api/v1/auth/logout")
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "recovering-estimator@ironhousecivil.com",
            "password": "temporary-password-2026",
        },
    )
    assert login.status_code == 200
    assert login.json()["user"]["password_reset_required"] is True
    assert client.get("/api/v1/projects").status_code == 403

    changed = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "temporary-password-2026",
            "new_password": "permanent-password-2026",
        },
    )
    assert changed.status_code == 200
    assert changed.json()["user"]["password_reset_required"] is False
    assert client.get("/api/v1/projects").status_code == 200

    with testing_session() as db:
        assert db.scalars(select(LoginThrottle)).all() == []

    events = list_recent_document_audit_events()
    rendered = json.dumps(events)
    assert "temporary-password-2026" not in rendered
    assert "permanent-password-2026" not in rendered
    assert any(
        event["action"] == "account_recovery"
        and event["request_id"] == "build-211-recovery"
        for event in events
    )
    assert any(event["action"] == "password_change" for event in events)
