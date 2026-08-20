from __future__ import annotations

from datetime import date
from io import BytesIO
import json
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from app.tools.staging_onboarding import (
    OnboardingDraft,
    StagingOnboardingClient,
    StagingOnboardingError,
    validate_staging_base_url,
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
