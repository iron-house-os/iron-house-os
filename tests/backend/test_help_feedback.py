from uuid import UUID

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.dependencies.auth import require_authenticated_user
from app.main import app
from app.models.help_feedback import HelpFeedback, HelpImprovement
from app.services.auth import AuthenticatedUser
from app.services.document_audit import (
    clear_recent_document_audit_events,
    list_recent_document_audit_events,
)
from conftest import TestingSessionLocal


client = TestClient(app)


def _principal(role: str = "viewer", email: str | None = None) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=UUID("00000000-0000-0000-0000-000000000046"),
        email=email or f"{role}46@example.com",
        display_name="Help Feedback User",
        role=role,
        session_version=1,
    )


def _use_user(user: AuthenticatedUser) -> None:
    def override(request: Request) -> AuthenticatedUser:
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = override


def _feedback(**updates) -> dict:
    payload = {
        "feedback_type": "not_helpful",
        "route": "/employee-portal/time",
        "project_name": "Bennett",
        "source_ids": ["employee-enter-time"],
        "note": "The save step was unclear.",
    }
    payload.update(updates)
    return payload


def test_employee_can_record_role_safe_help_feedback_without_question_storage() -> None:
    clear_recent_document_audit_events()
    user = _principal()
    _use_user(user)

    response = client.post(
        "/api/v1/help-coach/feedback",
        json=_feedback(),
        headers={"x-request-id": "help-feedback-employee"},
    )

    assert response.status_code == 201
    assert response.json()["recorded"] is True
    with TestingSessionLocal() as db:
        improvement = db.scalar(select(HelpImprovement))
        feedback = db.scalar(select(HelpFeedback))
        assert improvement is not None
        assert improvement.evidence_count == 1
        assert improvement.source_ids_json == ["employee-enter-time"]
        assert feedback is not None
        assert feedback.audience == "employee"
        assert feedback.note == "The save step was unclear."
        assert feedback.created_by == user.email
        assert "question" not in HelpFeedback.__table__.columns

    event = list_recent_document_audit_events(action="help_feedback_submit")[0]
    assert event["request_id"] == "help-feedback-employee"
    assert event["metadata"]["feedback_type"] == "not_helpful"
    assert "note" not in event["metadata"]
    assert "question" not in event["metadata"]


def test_repeated_feedback_aggregates_without_losing_evidence() -> None:
    _use_user(_principal())
    first = client.post("/api/v1/help-coach/feedback", json=_feedback(note="First note"))
    second = client.post("/api/v1/help-coach/feedback", json=_feedback(note="Second note"))

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["improvement_id"] == second.json()["improvement_id"]
    with TestingSessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(HelpImprovement)) == 1
        assert db.scalar(select(func.count()).select_from(HelpFeedback)) == 2
        improvement = db.scalar(select(HelpImprovement))
        assert improvement is not None
        assert improvement.evidence_count == 2
        assert improvement.latest_note == "Second note"


@pytest.mark.parametrize(
    ("payload", "detail"),
    [
        (_feedback(feedback_type="suggestion", note=""), "Tell us what you would improve"),
        (
            _feedback(feedback_type="suggestion", note="My payroll banking password is wrong"),
            "Do not include passwords",
        ),
    ],
)
def test_suggestions_require_safe_notes(payload: dict, detail: str) -> None:
    _use_user(_principal())

    response = client.post("/api/v1/help-coach/feedback", json=payload)

    assert response.status_code == 422
    assert detail in response.text
    with TestingSessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(HelpImprovement)) == 0
        assert db.scalar(select(func.count()).select_from(HelpFeedback)) == 0


def test_feedback_rejects_original_question_and_management_only_source() -> None:
    _use_user(_principal())

    question = client.post(
        "/api/v1/help-coach/feedback",
        json={**_feedback(), "question": "How do I enter my time?"},
    )
    management_source = client.post(
        "/api/v1/help-coach/feedback",
        json=_feedback(source_ids=["management-financial-control"]),
    )

    assert question.status_code == 422
    assert management_source.status_code == 422
    assert "available to your access level" in management_source.text


def test_management_can_review_aggregates_without_exposing_them_to_other_roles() -> None:
    _use_user(_principal())
    created = client.post("/api/v1/help-coach/feedback", json=_feedback())
    improvement_id = created.json()["improvement_id"]

    _use_user(_principal("operations_manager"))
    listed = client.get("/api/v1/help-coach/improvements")
    updated = client.patch(
        f"/api/v1/help-coach/improvements/{improvement_id}",
        json={"status": "reviewing", "review_note": "Confirm the save wording with the crew."},
    )

    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["evidence_count"] == 1
    evidence = client.get(f"/api/v1/help-coach/improvements/{improvement_id}/evidence")
    assert evidence.status_code == 200
    assert evidence.json()["total"] == 1
    assert evidence.json()["items"][0]["note"] == "The save step was unclear."
    assert "created_by" not in evidence.json()["items"][0]
    assert updated.status_code == 200
    assert updated.json()["status"] == "reviewing"
    assert updated.json()["reviewed_by"] == "operations_manager46@example.com"

    for role in ("viewer", "estimator"):
        _use_user(_principal(role))
        assert client.get("/api/v1/help-coach/improvements").status_code == 403
        assert client.get(
            f"/api/v1/help-coach/improvements/{improvement_id}/evidence"
        ).status_code == 403
        assert client.patch(
            f"/api/v1/help-coach/improvements/{improvement_id}",
            json={"status": "dismissed"},
        ).status_code == 403


def test_management_review_note_rejects_restricted_information() -> None:
    _use_user(_principal())
    created = client.post("/api/v1/help-coach/feedback", json=_feedback())
    _use_user(_principal("admin"))

    response = client.patch(
        f"/api/v1/help-coach/improvements/{created.json()['improvement_id']}",
        json={"status": "planned", "review_note": "Employee SIN is in the note"},
    )

    assert response.status_code == 422
    assert "restricted information" in response.text
