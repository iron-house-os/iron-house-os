from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.user import UserAccount
from app.services.auth import hash_password, verify_password


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
                email="jeremie@ironhousecivil.com",
                display_name="Jeremie Peters",
                role="admin",
                password_hash=hash_password("correct-horse-battery-staple"),
                is_active=True,
                session_version=1,
            )
        )
        db.commit()

    app = create_app()

    def override_db() -> Generator[Session, None, None]:
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app), testing_session


def test_password_hash_is_salted_and_verifiable() -> None:
    first = hash_password("correct-horse-battery-staple")
    second = hash_password("correct-horse-battery-staple")

    assert first != second
    assert verify_password("correct-horse-battery-staple", first)
    assert not verify_password("wrong-password", first)


def test_login_sets_http_only_cookie_and_returns_current_user() -> None:
    client, _ = _client()

    unauthenticated = client.get("/api/v1/auth/me")
    assert unauthenticated.status_code == 401

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "JEREMIE@IRONHOUSECIVIL.COM",
            "password": "correct-horse-battery-staple",
        },
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "jeremie@ironhousecivil.com"
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    assert client.get("/api/v1/auth/me").status_code == 200

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_login_rejects_wrong_credentials_without_account_disclosure() -> None:
    client, _ = _client()

    wrong_password = client.post(
        "/api/v1/auth/login",
        json={"email": "jeremie@ironhousecivil.com", "password": "wrong-password"},
    )
    unknown_email = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "wrong-password"},
    )

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_admin_can_create_users_and_new_user_cannot_administer_accounts() -> None:
    client, _ = _client()
    client.post(
        "/api/v1/auth/login",
        json={
            "email": "jeremie@ironhousecivil.com",
            "password": "correct-horse-battery-staple",
        },
    )

    created = client.post(
        "/api/v1/users",
        json={
            "email": "estimator@ironhousecivil.com",
            "display_name": "Iron House Estimator",
            "role": "estimator",
            "password": "estimate-password-2026",
        },
    )
    assert created.status_code == 201
    assert created.json()["role"] == "estimator"
    assert "password_hash" not in created.json()
    assert client.get("/api/v1/users").json()["total"] == 2

    client.post("/api/v1/auth/logout")
    client.post(
        "/api/v1/auth/login",
        json={
            "email": "estimator@ironhousecivil.com",
            "password": "estimate-password-2026",
        },
    )
    assert client.get("/api/v1/users").status_code == 403


def test_password_reset_invalidates_existing_session() -> None:
    client, testing_session = _client()
    client.post(
        "/api/v1/auth/login",
        json={
            "email": "jeremie@ironhousecivil.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert client.get("/api/v1/auth/me").status_code == 200

    with testing_session() as db:
        account = db.query(UserAccount).filter_by(email="jeremie@ironhousecivil.com").one()
        account.session_version += 1
        db.commit()

    assert client.get("/api/v1/auth/me").status_code == 401
