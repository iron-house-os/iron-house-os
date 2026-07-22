import json
from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient

from app.api.dependencies.auth import require_authenticated_user
from app.core.config import get_settings
from app.main import app
from app.services.auth import AuthenticatedUser

client = TestClient(app)


def _authenticate_as(role: str) -> None:
    def override(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            email=f"{role}@ironhousecivil.com",
            display_name=f"Test {role}", role=role, session_version=1,
        )
        request.state.authenticated_user = user
        return user
    app.dependency_overrides[require_authenticated_user] = override


def test_management_can_see_separate_assistant_status() -> None:
    response = client.get("/api/v1/iron-house-chat/status")
    assert response.status_code == 200
    assert response.json() == {
        "enabled": True,
        "configured": bool(get_settings().openai_api_key),
        "model": "gpt-5.6-sol",
        "mode": "read-only",
        "voice_supported": True,
        "memory_count": 7,
    }


def test_non_management_cannot_access_assistant() -> None:
    _authenticate_as("viewer")
    response = client.get("/api/v1/iron-house-chat/status")
    assert response.status_code == 403
    assert "iron-house-chat" in response.json()["detail"]


def test_missing_provider_credential_is_reported_without_exposing_secrets() -> None:
    response = client.post("/api/v1/iron-house-chat/messages", json={"message": "Where are cost codes?"})
    assert response.status_code == 200
    body = response.json()
    assert body["assistant_message"]["status"] == "unavailable"
    assert "credential" in body["assistant_message"]["content"]
    assert body["conversation"]["title"] == "Where are cost codes?"
    conversation_id = body["conversation"]["id"]
    history = client.get(f"/api/v1/iron-house-chat/conversations/{conversation_id}/messages")
    assert history.status_code == 200
    assert [item["role"] for item in history.json()] == ["user", "assistant"]


def test_chatgpt_export_import_keeps_project_threads_and_skips_unrelated_chats() -> None:
    export = [
        {
            "id": "ihos-thread-1", "title": "Build 43 Recovery Plan", "create_time": 1783620338,
            "mapping": {
                "1": {"message": {"create_time": 1, "author": {"role": "user"},
                                    "content": {"parts": ["Continue Iron House OS and repair Build 43."]}}},
                "2": {"message": {"create_time": 2, "author": {"role": "assistant"},
                                    "content": {"parts": ["The RFQ workflow needs repair."]}}},
            },
        },
        {
            "id": "personal-thread", "title": "Dinner ideas", "create_time": 1783620339,
            "mapping": {"1": {"message": {"create_time": 1, "author": {"role": "user"},
                                            "content": {"parts": ["What should I cook tonight?"]}}}},
        },
    ]
    response = client.post(
        "/api/v1/iron-house-chat/brain/import-chatgpt",
        files={"export": ("conversations.json", json.dumps(export), "application/json")},
    )
    assert response.status_code == 200
    assert response.json()["imported"] == 1
    assert response.json()["skipped"] == 1
    brain = client.get("/api/v1/iron-house-chat/brain")
    assert brain.status_code == 200
    assert any(item["source_id"] == "chatgpt:ihos-thread-1" for item in brain.json())
