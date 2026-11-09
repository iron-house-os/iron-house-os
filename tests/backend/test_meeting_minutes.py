from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient

from app.api.dependencies.auth import require_authenticated_user
from app.api.v1.routes import meeting_minutes as meeting_minutes_routes
from app.core.config import get_settings
from app.main import app
from app.schemas.meeting_minutes import MeetingActionItem, MeetingMinutesDraft
from app.services.auth import AuthenticatedUser

client = TestClient(app)


def _authenticate_as(role: str) -> None:
    def override(request: Request) -> AuthenticatedUser:
        user = AuthenticatedUser(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            email=f"{role}@ironhousecontracting.com",
            display_name=f"Test {role}",
            role=role,
            session_version=1,
        )
        request.state.authenticated_user = user
        return user

    app.dependency_overrides[require_authenticated_user] = override


def _draft(transcript: str, transcription_model: str | None = None) -> MeetingMinutesDraft:
    return MeetingMinutesDraft(
        transcript=transcript,
        summary="The excavation sequence and traffic control plan were reviewed.",
        priority_points=["Traffic control approval is required before mobilization."],
        decisions=["Mobilization remains scheduled for Monday."],
        action_items=[
            MeetingActionItem(task="Confirm traffic control approval.", owner="Jeremie", due_date="2026-07-27")
        ],
        transcription_model=transcription_model,
        summary_model="gpt-5.6-sol",
        audio_retained=False,
    )


def test_management_can_see_privacy_and_model_status() -> None:
    response = client.get("/api/v1/meeting-minutes/status")
    assert response.status_code == 200
    assert response.json() == {
        "enabled": True,
        "configured": bool(get_settings().openai_api_key),
        "transcription_model": "gpt-4o-mini-transcribe",
        "summary_model": "gpt-5.6-sol",
        "max_audio_bytes": 25 * 1024 * 1024,
        "audio_retained": False,
    }


def test_recording_requires_explicit_consent_before_provider_use() -> None:
    response = client.post(
        "/api/v1/meeting-minutes/draft-from-audio",
        data={"title": "Site meeting", "consent_confirmed": "false"},
        files={"audio": ("meeting.webm", b"recording", "audio/webm")},
    )
    assert response.status_code == 400
    assert "everyone present" in response.json()["detail"]


def test_unsupported_audio_is_rejected_before_provider_use() -> None:
    response = client.post(
        "/api/v1/meeting-minutes/draft-from-audio",
        data={"title": "Site meeting", "consent_confirmed": "true"},
        files={"audio": ("meeting.ogg", b"recording", "audio/ogg")},
    )
    assert response.status_code == 400
    assert "Unsupported recording format" in response.json()["detail"]


def test_audio_is_transcribed_to_a_reviewable_draft_without_retention(monkeypatch) -> None:
    monkeypatch.setattr(
        meeting_minutes_routes,
        "transcribe_audio",
        lambda content, content_type: ("Jeremie confirmed Monday mobilization.", "test-transcriber"),
    )
    monkeypatch.setattr(
        meeting_minutes_routes,
        "draft_minutes",
        lambda transcript, title, attendees, transcription_model=None: _draft(
            transcript, transcription_model
        ),
    )
    response = client.post(
        "/api/v1/meeting-minutes/draft-from-audio",
        data={
            "title": "Site meeting",
            "attendees": "Jeremie, Superintendent",
            "consent_confirmed": "true",
        },
        files={"audio": ("meeting.webm", b"recording", "audio/webm")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["transcript"] == "Jeremie confirmed Monday mobilization."
    assert body["priority_points"] == ["Traffic control approval is required before mobilization."]
    assert body["transcription_model"] == "test-transcriber"
    assert body["audio_retained"] is False


def test_reviewed_minutes_can_be_saved_and_listed() -> None:
    payload = {
        "title": "Operations meeting",
        "project_id": None,
        "meeting_date": "2026-07-25T19:00:00-07:00",
        "attendees": ["Jeremie", "Superintendent"],
        "transcript": "The team reviewed Monday mobilization.",
        "summary": "Monday mobilization remains scheduled.",
        "priority_points": ["Traffic control approval is still required."],
        "decisions": ["Keep the Monday mobilization date."],
        "action_items": [
            {"task": "Confirm traffic control approval.", "owner": "Jeremie", "due_date": "2026-07-27"}
        ],
        "transcription_model": "gpt-4o-mini-transcribe",
        "summary_model": "gpt-5.6-sol",
        "consent_confirmed": True,
        "review_confirmed": True,
    }
    saved = client.post("/api/v1/meeting-minutes", json=payload)
    assert saved.status_code == 201
    body = saved.json()
    assert body["status"] == "approved"
    assert body["audio_retained"] is False
    assert body["consent_confirmed"] is True
    assert body["review_confirmed"] is True
    assert body["action_items"][0]["owner"] == "Jeremie"

    listing = client.get("/api/v1/meeting-minutes")
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [body["id"]]
    assert "transcript" not in listing.json()[0]


def test_minutes_cannot_be_approved_without_management_review() -> None:
    response = client.post(
        "/api/v1/meeting-minutes",
        json={
            "title": "Unreviewed meeting",
            "meeting_date": "2026-07-25T19:00:00-07:00",
            "transcript": "Unreviewed transcript.",
            "summary": "Unreviewed summary.",
            "summary_model": "gpt-5.6-sol",
            "consent_confirmed": True,
            "review_confirmed": False,
        },
    )
    assert response.status_code == 400
    assert "Management review" in response.json()["detail"]


def test_non_management_cannot_access_meeting_minutes() -> None:
    _authenticate_as("estimator")
    response = client.get("/api/v1/meeting-minutes/status")
    assert response.status_code == 403
    assert "meeting-minutes" in response.json()["detail"]
