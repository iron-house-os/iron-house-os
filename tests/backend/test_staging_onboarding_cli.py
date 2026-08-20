from __future__ import annotations

from datetime import date
from io import BytesIO
import json
import stat
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from app.tools.staging_onboarding import (
    OnboardingDraft,
    InvitationLink,
    RosterRecord,
    StagingOnboardingClient,
    StagingOnboardingError,
    validate_staging_base_url,
    write_invitation_handoff,
)


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self.body = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


class FakeOpener:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.requests: list[Request] = []

    def open(self, request: Request, timeout: float = 0):
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return FakeResponse(response)


@pytest.mark.parametrize(
    "url",
    [
        "https://os.ironhousecivil.com",
        "http://staging.os.ironhousecivil.com",
        "https://staging.os.ironhousecivil.com.example.com",
        "https://staging.os.ironhousecivil.com/other",
        "https://user:password@staging.os.ironhousecivil.com",
    ],
)
def test_staging_helper_refuses_production_and_arbitrary_hosts(url: str) -> None:
    with pytest.raises(StagingOnboardingError, match="locked"):
        validate_staging_base_url(url)


def test_login_failure_does_not_echo_credentials() -> None:
    error = HTTPError(
        url="https://staging.os.ironhousecivil.com/api/v1/auth/login",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=BytesIO(b'{"detail":"Email or password is incorrect."}'),
    )
    client = StagingOnboardingClient(opener=FakeOpener([error]))

    with pytest.raises(StagingOnboardingError) as caught:
        client.login("administrator@example.com", "top-secret-password")

    rendered = str(caught.value)
    assert "administrator@example.com" not in rendered
    assert "top-secret-password" not in rendered


def test_existing_email_is_skipped_without_creating_duplicate() -> None:
    opener = FakeOpener([
        {"items": [{"personal_email": "person@example.com"}]},
    ])
    client = StagingOnboardingClient(opener=opener)

    result = client.create_draft(
        OnboardingDraft(
            legal_first_name="Test",
            legal_last_name="Person",
            personal_email="PERSON@example.com",
            position="cfo",
            start_date=date(2026, 8, 20),
        )
    )

    assert result.outcome == "already_exists"
    assert result.onboarding_id is None
    assert len(opener.requests) == 1
    assert opener.requests[0].get_method() == "GET"


def test_successful_staging_draft_creation_uses_office_staff_payload() -> None:
    opener = FakeOpener([
        {"items": []},
        {"id": "9d07e5a7-a973-4d38-9c63-f42ee8688186"},
    ])
    client = StagingOnboardingClient(opener=opener)

    result = client.create_draft(
        OnboardingDraft(
            legal_first_name="Test",
            legal_last_name="Executive",
            personal_email="Executive@example.com",
            position="president",
            start_date=date(2026, 8, 20),
        )
    )

    assert result.outcome == "created"
    assert result.onboarding_id == "9d07e5a7-a973-4d38-9c63-f42ee8688186"
    assert len(opener.requests) == 2
    create_request = opener.requests[1]
    assert create_request.get_method() == "POST"
    payload = json.loads(create_request.data or b"{}")
    assert payload["personal_email"] == "executive@example.com"
    assert payload["category"] == "office_staff"
    assert payload["position"] == "president"


def test_position_verification_requires_all_executive_titles() -> None:
    opener = FakeOpener([[{"value": "ceo"}, {"value": "president"}]])
    client = StagingOnboardingClient(opener=opener)

    with pytest.raises(StagingOnboardingError, match="cfo"):
        client.verify_positions({"ceo", "president", "cfo"})


def _record(first_name: str, last_name: str, position: str, identifier: str) -> dict[str, str]:
    return {
        "id": identifier,
        "legal_first_name": first_name,
        "legal_last_name": last_name,
        "position": position,
        "status": "draft",
    }


def test_exact_executive_roster_records_are_resolved() -> None:
    opener = FakeOpener(
        [
            {
                "items": [
                    _record("Mack", "Warren", "ceo", "mack-id"),
                    _record("Jeremie", "Peters", "president", "jeremie-id"),
                    _record("Stefani", "Warren", "cfo", "stefani-id"),
                ]
            }
        ]
    )
    client = StagingOnboardingClient(opener=opener)

    records = client.executive_roster_records()

    assert [record.onboarding_id for record in records] == ["mack-id", "jeremie-id", "stefani-id"]


@pytest.mark.parametrize("duplicate", [False, True])
def test_missing_or_ambiguous_roster_record_is_refused(duplicate: bool) -> None:
    mack = _record("Mack", "Warren", "ceo", "mack-id")
    items = [mack, _record("Jeremie", "Peters", "president", "jeremie-id")]
    if duplicate:
        items.append({**mack, "id": "second-mack-id"})
    opener = FakeOpener([{"items": items}])
    client = StagingOnboardingClient(opener=opener)

    with pytest.raises(StagingOnboardingError, match="missing|ambiguous"):
        client.executive_roster_records()


def test_fresh_invitation_is_issued_for_selected_record() -> None:
    opener = FakeOpener(
        [
            {
                "invite_url": "https://staging.os.ironhousecivil.com/employee-onboarding/secure-token",
                "expires_at": "2026-08-23T10:00:00Z",
            }
        ]
    )
    client = StagingOnboardingClient(opener=opener)
    record = RosterRecord(
        onboarding_id="mack-id",
        legal_first_name="Mack",
        legal_last_name="Warren",
        position="ceo",
        label="CEO",
        status="draft",
    )

    invitation = client.issue_invitation(record)

    assert invitation.worker_name == "Mack Warren"
    assert invitation.label == "CEO"
    assert opener.requests[0].get_method() == "POST"
    assert opener.requests[0].full_url.endswith("/employee-onboarding/mack-id/invite")


def test_invitation_handoff_file_is_private_and_contains_current_link(tmp_path) -> None:
    invitation = InvitationLink(
        worker_name="Test Worker",
        label="CEO",
        invite_url="https://staging.os.ironhousecivil.com/employee-onboarding/secure-token",
        expires_at="2026-08-23T10:00:00Z",
    )

    path = write_invitation_handoff([invitation], directory=tmp_path)

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    content = path.read_text()
    assert "Test Worker — CEO" in content
    assert "secure-token" in content
