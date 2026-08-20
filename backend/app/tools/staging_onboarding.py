"""Interactive, staging-only employee onboarding draft creator."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from getpass import getpass
import json
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener
from http.cookiejar import CookieJar


STAGING_BASE_URL = "https://staging.os.ironhousecivil.com"
API_PREFIX = "/api/v1"


class StagingOnboardingError(RuntimeError):
    """Raised when the staging onboarding helper cannot safely continue."""


class ResponseLike(Protocol):
    def __enter__(self) -> ResponseLike: ...

    def __exit__(self, *args: object) -> None: ...

    def read(self) -> bytes: ...


class OpenerLike(Protocol):
    def open(self, request: Request, timeout: float = 0) -> ResponseLike: ...


@dataclass(frozen=True)
class OnboardingDraft:
    legal_first_name: str
    legal_last_name: str
    personal_email: str
    position: str
    start_date: date
    employment_type: str = "salary"
    primary_location: str | None = "Iron House Office"
    onboarding_package: str | None = "office_staff"


@dataclass(frozen=True)
class DraftResult:
    outcome: str
    onboarding_id: str | None
    position: str


EXECUTIVE_STAGING_ROSTER = (
    ("Mack", "Warren", "ceo", "CEO"),
    ("Jeremie", "Peters", "president", "President"),
    ("Stefani", "Warren", "cfo", "CFO"),
)


def validate_staging_base_url(base_url: str) -> str:
    """Return the canonical staging origin or refuse the target."""
    parsed = urlsplit(base_url.strip())
    if (
        parsed.scheme != "https"
        or parsed.hostname != "staging.os.ironhousecivil.com"
        or parsed.port not in {None, 443}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise StagingOnboardingError(
            "This helper is locked to https://staging.os.ironhousecivil.com and refuses production or arbitrary hosts."
        )
    return STAGING_BASE_URL


class StagingOnboardingClient:
    def __init__(
        self,
        *,
        base_url: str = STAGING_BASE_URL,
        opener: OpenerLike | None = None,
        timeout: float = 20,
    ) -> None:
        self.base_url = validate_staging_base_url(base_url)
        self.opener = opener or build_opener(HTTPCookieProcessor(CookieJar()))
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        encoded = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{API_PREFIX}{path}",
            data=encoded,
            method=method,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                body = response.read()
        except HTTPError as exc:
            if exc.code == 401:
                raise StagingOnboardingError("Staging sign-in failed. Check the administrator email and password.") from exc
            if exc.code == 403:
                raise StagingOnboardingError("The signed-in account does not have staging administrator access.") from exc
            raise StagingOnboardingError(f"Staging API request failed with HTTP {exc.code}.") from exc
        except URLError as exc:
            raise StagingOnboardingError("The staging API could not be reached.") from exc
        if not body:
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise StagingOnboardingError("The staging API returned an invalid response.") from exc

    def login(self, email: str, password: str) -> None:
        response = self._request("POST", "/auth/login", {"email": email, "password": password})
        user = response.get("user", {}) if isinstance(response, dict) else {}
        if user.get("role") != "admin":
            raise StagingOnboardingError("The signed-in account is not a staging administrator.")

    def verify_positions(self, expected: set[str]) -> None:
        response = self._request("GET", "/employee-onboarding/positions")
        available = {
            item.get("value")
            for item in response
            if isinstance(item, dict) and isinstance(item.get("value"), str)
        }
        missing = expected - available
        if missing:
            raise StagingOnboardingError(
                "Staging is missing required controlled positions: " + ", ".join(sorted(missing))
            )

    def create_draft(self, draft: OnboardingDraft) -> DraftResult:
        records = self._request("GET", "/employee-onboarding")
        items = records.get("items", []) if isinstance(records, dict) else []
        normalized_email = draft.personal_email.strip().lower()
        if any(
            isinstance(item, dict)
            and str(item.get("personal_email", "")).strip().lower() == normalized_email
            for item in items
        ):
            return DraftResult(outcome="already_exists", onboarding_id=None, position=draft.position)

        response = self._request(
            "POST",
            "/employee-onboarding",
            {
                "legal_first_name": draft.legal_first_name,
                "legal_last_name": draft.legal_last_name,
                "personal_email": normalized_email,
                "category": "office_staff",
                "position": draft.position,
                "employment_type": draft.employment_type,
                "start_date": draft.start_date.isoformat(),
                "primary_location": draft.primary_location,
                "onboarding_package": draft.onboarding_package,
            },
        )
        onboarding_id = response.get("id") if isinstance(response, dict) else None
        if not isinstance(onboarding_id, str) or not onboarding_id:
            raise StagingOnboardingError("Staging created a draft but did not return its record ID.")
        return DraftResult(outcome="created", onboarding_id=onboarding_id, position=draft.position)

    def logout(self) -> None:
        self._request("POST", "/auth/logout")


def _prompt_date(prompt: str, default: date) -> date:
    raw = input(f"{prompt} [{default.isoformat()}]: ").strip()
    if not raw:
        return default
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise StagingOnboardingError("Start date must use YYYY-MM-DD format.") from exc


def run_interactive(client: StagingOnboardingClient) -> int:
    print("Iron House OS staging onboarding helper")
    print("Creates drafts only. It does not invite, approve, orient, activate, or generate passwords.")
    admin_email = input("Staging administrator email: ").strip()
    admin_password = getpass("Staging administrator password (hidden): ")
    try:
        client.login(admin_email, admin_password)
    finally:
        del admin_password

    client.verify_positions({"ceo", "president", "cfo"})
    start_date = _prompt_date("Start date for these staging records", date.today())
    created = 0
    existing = 0

    try:
        for first_name, last_name, position, label in EXECUTIVE_STAGING_ROSTER:
            print(f"\n{first_name} {last_name} — {label}")
            employee_email = input("Employee email/username: ").strip()
            if not employee_email:
                raise StagingOnboardingError("An employee email is required for every staging draft.")
            confirm = input("Create this staging draft? [y/N]: ").strip().lower()
            if confirm not in {"y", "yes"}:
                print("Skipped.")
                continue
            result = client.create_draft(
                OnboardingDraft(
                    legal_first_name=first_name,
                    legal_last_name=last_name,
                    personal_email=employee_email,
                    position=position,
                    start_date=start_date,
                )
            )
            if result.outcome == "already_exists":
                existing += 1
                print(f"Existing {label} onboarding draft found; no duplicate was created.")
            else:
                created += 1
                print(f"Created {label} onboarding draft (record {result.onboarding_id}).")
    finally:
        client.logout()

    print(f"\nComplete: {created} created, {existing} already existed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=STAGING_BASE_URL, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        return run_interactive(StagingOnboardingClient(base_url=args.base_url))
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled. No further records were created.")
        return 130
    except StagingOnboardingError as exc:
        print(f"Stopped: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
