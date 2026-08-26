import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.dependencies.auth import require_authenticated_user
from app.api.v1.routes import help_coach as help_coach_route
from app.main import app
from app.models.assistant import AssistantConversation
from app.models.user import Employee
from app.services.auth import AuthenticatedUser
from app.services.document_audit import (
    clear_recent_document_audit_events,
    list_recent_document_audit_events,
)
from app.services import iron_house_chat
from app.services.help_coach import APPROVED_HELP_ARTICLES
from app.services.iron_house_chat import AssistantUnavailable
from conftest import TestingSessionLocal


client = TestClient(app)


class _ProviderResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps({"output_text": "Use the approved guide."}).encode()


def _principal(email: str, role: str = "viewer") -> AuthenticatedUser:
    return AuthenticatedUser(
        id=UUID("00000000-0000-0000-0000-000000000039"),
        email=email,
        display_name="Help Coach User",
        role=role,
        session_version=1,
    )


def _use_user(user: AuthenticatedUser) -> None:
    def override(request: Request) -> AuthenticatedUser:
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = override


def _disable_provider(monkeypatch) -> None:
    monkeypatch.setattr(
        help_coach_route,
        "get_settings",
        lambda: SimpleNamespace(iron_house_chat_enabled=False, openai_api_key=""),
    )


def test_employee_gets_grounded_static_help_without_creating_chat_records(monkeypatch) -> None:
    clear_recent_document_audit_events()
    _disable_provider(monkeypatch)
    user = _principal("employee39@example.com")
    _use_user(user)
    with TestingSessionLocal() as db:
        db.add(
            Employee(
                first_name="Evan",
                last_name="Employee",
                email=user.email,
                portal_role="employee",
            )
        )
        db.commit()

    response = client.post(
        "/api/v1/help-coach/messages",
        json={"message": "How do I enter my hours?", "route": "/employee-portal/time"},
        headers={"x-request-id": "help-coach-employee"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["audience"] == "employee"
    assert body["status"] == "static_fallback"
    assert body["mode"] == "read-only"
    assert body["sources"][0]["id"] == "employee-enter-time"
    assert all(not item["id"].startswith("management-") for item in body["sources"])
    assert all(not item["id"].startswith("foreman-") for item in body["sources"])
    with TestingSessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(AssistantConversation)) == 0

    event = list_recent_document_audit_events(action="help_coach_request")[0]
    assert event["request_id"] == "help-coach-employee"
    assert event["metadata"]["audience"] == "employee"
    assert event["metadata"]["source_ids"][0] == "employee-enter-time"
    assert "message" not in event["metadata"]


def test_server_resolves_foreman_audience_from_employee_record(monkeypatch) -> None:
    _disable_provider(monkeypatch)
    user = _principal("foreman39@example.com")
    _use_user(user)
    with TestingSessionLocal() as db:
        db.add(
            Employee(
                first_name="Fran",
                last_name="Foreman",
                email=user.email,
                portal_role="foreman",
            )
        )
        db.commit()

    response = client.post(
        "/api/v1/help-coach/messages",
        json={"message": "How do I enter crew time?", "route": "/foreman-portal/time"},
    )

    assert response.status_code == 200
    assert response.json()["audience"] == "foreman"
    assert response.json()["sources"][0]["id"] == "foreman-crew-time"
    assert all(
        not item["id"].startswith("management-") for item in response.json()["sources"]
    )


def test_estimator_uses_management_help_without_opening_project_brain(monkeypatch) -> None:
    _disable_provider(monkeypatch)
    _use_user(_principal("estimator39@example.com", "estimator"))

    response = client.post(
        "/api/v1/help-coach/messages",
        json={"message": "How do I build an estimate?", "route": "/estimating"},
    )

    assert response.status_code == 200
    assert response.json()["audience"] == "management"
    assert response.json()["sources"][0]["id"] == "management-build-estimate"


def test_provider_receives_only_approved_role_safe_help_context(monkeypatch) -> None:
    clear_recent_document_audit_events()
    captured: dict[str, str] = {}
    user = _principal("employee-provider39@example.com")
    _use_user(user)
    with TestingSessionLocal() as db:
        db.add(
            Employee(
                first_name="Pat",
                last_name="Provider",
                email=user.email,
                portal_role="employee",
            )
        )
        db.commit()
    monkeypatch.setattr(
        help_coach_route,
        "get_settings",
        lambda: SimpleNamespace(iron_house_chat_enabled=True, openai_api_key="test-key"),
    )

    def fake_reply(
        message: str,
        approved_context: str,
        *,
        route: str,
        project_name: str,
    ) -> str:
        captured.update(
            message=message,
            approved_context=approved_context,
            route=route,
            project_name=project_name,
        )
        return "Use the approved Submit a receipt guide."

    monkeypatch.setattr(help_coach_route, "generate_help_coach_reply", fake_reply)

    response = client.post(
        "/api/v1/help-coach/messages",
        json={
            "message": "Where do I submit a receipt?",
            "route": "/employee-portal/receipts",
            "project_name": "Bennett",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert "employee-submit-receipt" in captured["approved_context"]
    assert "management-verbal-quote" not in captured["approved_context"]
    assert "PROJECT BRAIN" not in captured["approved_context"]
    assert captured["project_name"] == "Bennett"
    event = list_recent_document_audit_events(action="help_coach_request")[0]
    assert event["metadata"]["provider_status"] == "completed"


def test_help_coach_provider_payload_never_contains_project_brain(monkeypatch) -> None:
    captured: dict = {}
    monkeypatch.setattr(
        iron_house_chat,
        "get_settings",
        lambda: SimpleNamespace(
            openai_api_key="test-key",
            openai_api_base_url="https://api.openai.test/v1",
            openai_chat_model="gpt-test",
        ),
    )

    def fake_urlopen(request, timeout: int):
        captured.update(json.loads(request.data.decode()))
        assert timeout == 45
        return _ProviderResponse()

    monkeypatch.setattr(iron_house_chat, "urlopen", fake_urlopen)

    answer = iron_house_chat.generate_help_coach_reply(
        "How do I enter time?",
        "ARTICLE ID: employee-enter-time\nTITLE: Enter my time",
        route="/employee-portal/time",
        project_name="Bennett",
    )

    assert answer == "Use the approved guide."
    assert "PROJECT BRAIN" not in captured["instructions"]
    assert "APPROVED HELP ARTICLES" in captured["instructions"]
    assert captured["input"] == "How do I enter time?"


def test_server_help_registry_ids_exist_in_the_merged_static_help_registry() -> None:
    registry = (
        Path(__file__).resolve().parents[2] / "frontend" / "src" / "helpArticles.ts"
    ).read_text(encoding="utf-8")
    ids = [article.id for article in APPROVED_HELP_ARTICLES]
    assert len(ids) == len(set(ids))
    for article_id in ids:
        assert f'id: "{article_id}"' in registry


def test_provider_failure_keeps_approved_static_help_available(monkeypatch) -> None:
    _use_user(_principal("manager39@example.com", "operations_manager"))
    monkeypatch.setattr(
        help_coach_route,
        "get_settings",
        lambda: SimpleNamespace(iron_house_chat_enabled=True, openai_api_key="test-key"),
    )
    monkeypatch.setattr(
        help_coach_route,
        "generate_help_coach_reply",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssistantUnavailable("offline")),
    )

    response = client.post(
        "/api/v1/help-coach/messages",
        json={"message": "How do I create a project?", "route": "/projects"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "static_fallback"
    assert "Open Projects" in response.json()["answer"]


def test_restricted_information_is_blocked_before_provider_call(monkeypatch) -> None:
    _use_user(_principal("private39@example.com"))
    monkeypatch.setattr(
        help_coach_route,
        "generate_help_coach_reply",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not call provider")),
    )

    response = client.post(
        "/api/v1/help-coach/messages",
        json={"message": "My password is forbidden-value. Where should I save it?"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "restricted"
    assert response.json()["sources"] == []
    assert "forbidden-value" not in response.json()["answer"]


def test_unknown_question_does_not_invite_an_ungrounded_answer(monkeypatch) -> None:
    _disable_provider(monkeypatch)
    _use_user(_principal("unknown39@example.com"))

    response = client.post(
        "/api/v1/help-coach/messages",
        json={"message": "Calibrate the orbital spectrometer"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "no_match"
    assert response.json()["sources"] == []
    assert "cannot guess" in response.json()["answer"]
