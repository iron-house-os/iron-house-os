import asyncio
from datetime import UTC, datetime
from time import time
from uuid import uuid4

import httpx
import pytest
from jose import jwt
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.chat_connector import ConnectorSettings, IntrospectionVerifier, create_connector
from app.core.config import get_settings
from app.db.base import Base
from app.models.project import Project
from app.models.user import UserAccount
from app.services.chat_projects import TenderIntake, apply_intake, preview_intake, project_inventory


@pytest.fixture
def database():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        manager = UserAccount(email="manager@example.com", display_name="Manager", role="admin",
                              password_hash="not-a-login", is_active=True, password_reset_required=False)
        db.add(manager)
        db.commit()
        yield db, manager


def intake(**changes):
    return TenderIntake(source_folder_id="verified_folder_123", name="Example tender", **changes)


def settings(**changes):
    values = dict(enabled=True, resource_url="https://staging.os.example.com/mcp",
                  issuer_url="https://identity.example.com/", introspection_url="https://identity.example.com/introspect",
                  introspection_client_id="ihos-resource", introspection_client_secret="test-only-not-production",
                  allowed_client_ids=["chat-client"], subject_accounts={"owner": uuid4()})
    return ConnectorSettings(**(values | changes))


def introspection(**changes):
    return dict(active=True, iss="https://identity.example.com/", aud="https://staging.os.example.com/mcp",
                exp=int(time()) + 300, client_id="chat-client", sub="owner", scope="ihos:projects:read") | changes


def verify(payload, config=None, status=200):
    transport = httpx.MockTransport(lambda request: httpx.Response(status, json=payload))
    return asyncio.run(IntrospectionVerifier(config or settings(), transport).verify_token("test-token"))


def test_introspection_validates_the_resource_owner_not_the_client_identity():
    config = settings()
    token = verify(introspection(), config)
    assert token.subject == "owner"
    assert token.client_id == "chat-client"
    assert token.claims["account_id"] == str(config.subject_accounts["owner"])


@pytest.mark.parametrize("change", [
    {"active": False}, {"active": "true"}, {"iss": "https://other.example.com/"},
    {"aud": "https://other.example.com/mcp"}, {"exp": int(time()) - 1},
    {"exp": int(time()) + 7200}, {"exp": "9999999999"}, {"sub": "unlinked-user"},
    {"client_id": "unapproved-client"}, {"scope": "ihos:projects:write"}, {"scope": ["ihos:projects:read"]},
])
def test_invalid_oauth_grants_are_rejected(change):
    assert verify(introspection(**change)) is None


def test_introspection_redirect_and_provider_failure_are_rejected():
    assert verify({}, status=302) is None
    assert verify({}, status=503) is None
    assert verify(introspection(), settings(enabled=False)) is None


def test_connector_requires_https_and_explicit_enablement():
    with pytest.raises(ValueError):
        settings(introspection_url="http://identity.example.com/introspect")
    with pytest.raises(RuntimeError):
        create_connector(settings(enabled=False))


def test_http_endpoint_refuses_unauthenticated_requests():
    from starlette.testclient import TestClient
    server = create_connector(settings())
    with TestClient(server.streamable_http_app(), base_url="http://127.0.0.1:8091") as client:
        response = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert response.status_code == 401
        assert "resource_metadata" in response.headers["www-authenticate"]


def test_preview_has_no_write_and_apply_is_idempotent(database):
    db, manager = database
    preview = preview_intake(db, manager, intake())
    assert db.scalar(select(func.count(Project.id))) == 0
    created = apply_intake(db, manager, preview["preview_token"])
    retried = apply_intake(db, manager, preview["preview_token"])
    assert created["id"] == retried["id"]
    assert created["status"] == "opportunity" and created["project_number"] is None
    assert retried["operation"] == "verified_existing"
    assert db.scalar(select(func.count(Project.id))) == 1


@pytest.mark.parametrize("role,active,reset", [("employee", True, False), ("viewer", True, False),
                                             ("admin", False, False), ("admin", True, True)])
def test_account_state_is_enforced_on_every_operation(database, role, active, reset):
    db, manager = database
    preview = preview_intake(db, manager, intake())
    manager.role, manager.is_active, manager.password_reset_required = role, active, reset
    for operation in (lambda: project_inventory(db, manager), lambda: apply_intake(db, manager, preview["preview_token"])):
        with pytest.raises(PermissionError):
            operation()


def test_preview_cannot_be_reused_by_another_account_or_after_password_version_changes(database):
    db, manager = database
    preview = preview_intake(db, manager, intake())
    manager.session_version += 1
    with pytest.raises(ValueError):
        apply_intake(db, manager, preview["preview_token"])


def test_expired_and_tampered_previews_are_rejected(database):
    db, manager = database
    preview = preview_intake(db, manager, intake())
    token = preview["preview_token"]
    with pytest.raises(ValueError):
        apply_intake(db, manager, token + "tampered")
    claims = jwt.get_unverified_claims(token)
    claims["exp"] = int(time()) - 1
    expired = jwt.encode(claims, get_settings().secret_key, algorithm="HS256")
    with pytest.raises(ValueError):
        apply_intake(db, manager, expired)


def test_ambiguous_or_trashed_projects_are_not_recreated(database):
    db, manager = database
    db.add(Project(name="Example tender", status="awarded", project_number="IH2026001"))
    db.commit()
    assert preview_intake(db, manager, intake())["action"] == "conflict"
    existing = db.scalar(select(Project))
    existing.deleted_at = datetime.now(UTC)
    db.commit()
    assert preview_intake(db, manager, intake())["action"] == "conflict"
    assert db.scalar(select(func.count(Project.id))) == 1


def test_inventory_change_invalidates_a_create_preview(database):
    db, manager = database
    preview = preview_intake(db, manager, intake())
    db.add(Project(name="Example tender", status="construction"))
    db.commit()
    with pytest.raises(ValueError):
        apply_intake(db, manager, preview["preview_token"])


def test_source_content_changes_do_not_overwrite_existing_projects(database):
    db, manager = database
    preview = preview_intake(db, manager, intake())
    apply_intake(db, manager, preview["preview_token"])
    changed = intake(client_owner="Different customer")
    assert preview_intake(db, manager, changed)["action"] == "conflict"


def test_intake_cannot_inject_award_finance_or_safety_controls():
    for extra in ({"status": "awarded"}, {"project_number": "IH2026001"},
                  {"metadata": {"safety_launch": {"ready": True}}}, {"contract_value": 100}):
        with pytest.raises(ValueError):
            intake(**extra)


def test_bounded_inventory_and_no_secret_fields(database):
    db, manager = database
    for name in ("A", "B"):
        db.add(Project(name=name, status="opportunity"))
    db.commit()
    result = project_inventory(db, manager, limit=1)
    assert len(result["items"]) == 1 and result["next_offset"] == 1
    assert "password_hash" not in str(result)
    with pytest.raises(ValueError):
        project_inventory(db, manager, limit=1000)
