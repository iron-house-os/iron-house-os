from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import base64
import hashlib
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

INTUIT_AUTHORIZATION_URL = "https://appcenter.intuit.com/connect/oauth2"
INTUIT_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
INTUIT_REVOKE_URL = "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"
QUICKBOOKS_SANDBOX_API_URL = "https://sandbox-quickbooks.api.intuit.com"
REQUIRED_SCOPE = "com.intuit.quickbooks.accounting"


class QuickBooksUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class QuickBooksTokenResult:
    access_token: str
    refresh_token: str | None
    expires_at: datetime
    refresh_token_expires_at: datetime | None
    scopes: list[str]


@dataclass(frozen=True)
class QuickBooksCompanyInfo:
    company_name: str
    legal_name: str | None


def quickbooks_is_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.quickbooks_environment.strip().lower() == "sandbox"
        and settings.quickbooks_client_id
        and settings.quickbooks_client_secret
        and settings.quickbooks_redirect_uri
        and settings.quickbooks_token_encryption_key
    )


def authorization_url(state: str) -> str:
    settings = get_settings()
    if not quickbooks_is_configured():
        raise QuickBooksUnavailable("QuickBooks sandbox OAuth is not configured.")
    return f"{INTUIT_AUTHORIZATION_URL}?{urlencode({
        'client_id': settings.quickbooks_client_id,
        'redirect_uri': settings.quickbooks_redirect_uri,
        'response_type': 'code',
        'scope': REQUIRED_SCOPE,
        'state': state,
    })}"


def state_digest(state: str) -> str:
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def encrypt_token(token: str) -> str:
    return _cipher().encrypt(token.encode("utf-8")).decode("ascii")


def decrypt_token(encrypted_token: str) -> str:
    try:
        return _cipher().decrypt(encrypted_token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
        raise QuickBooksUnavailable(
            "The stored QuickBooks connection cannot be decrypted. Reconnect QuickBooks."
        ) from exc


def exchange_authorization_code(
    code: str,
    existing_refresh_token: str | None = None,
) -> QuickBooksTokenResult:
    settings = get_settings()
    result = _form_request(
        INTUIT_TOKEN_URL,
        {
            "code": code,
            "redirect_uri": settings.quickbooks_redirect_uri,
            "grant_type": "authorization_code",
        },
    )
    return _token_result(result, existing_refresh_token=existing_refresh_token)


def get_company_info(access_token: str, realm_id: str) -> QuickBooksCompanyInfo:
    if not realm_id.isdigit() or len(realm_id) > 64:
        raise QuickBooksUnavailable("QuickBooks returned an invalid company identifier.")
    safe_realm = quote(realm_id, safe="")
    payload = _json_request(
        f"{QUICKBOOKS_SANDBOX_API_URL}/v3/company/{safe_realm}/companyinfo/{safe_realm}?minorversion=75",
        access_token=access_token,
    )
    raw = payload.get("CompanyInfo")
    if not isinstance(raw, dict) or not raw.get("CompanyName"):
        raise QuickBooksUnavailable("QuickBooks returned no company identity.")
    legal_name = raw.get("LegalName")
    return QuickBooksCompanyInfo(
        company_name=str(raw["CompanyName"])[:255],
        legal_name=str(legal_name)[:255] if legal_name else None,
    )


def revoke_token(token: str) -> None:
    request = Request(
        INTUIT_REVOKE_URL,
        data=json.dumps({"token": token}).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Authorization": _basic_authorization(),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    _read_json_response(request)


def _cipher() -> Fernet:
    source = get_settings().quickbooks_token_encryption_key
    if not source:
        raise QuickBooksUnavailable("QuickBooks token encryption is not configured.")
    key = base64.urlsafe_b64encode(hashlib.sha256(source.encode("utf-8")).digest())
    return Fernet(key)


def _basic_authorization() -> str:
    settings = get_settings()
    client_id = settings.quickbooks_client_id or ""
    client_secret = settings.quickbooks_client_secret or ""
    encoded = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    return f"Basic {encoded}"


def _form_request(url: str, fields: dict[str, str]) -> dict:
    request = Request(
        url,
        data=urlencode(fields).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Authorization": _basic_authorization(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    return _read_json_response(request)


def _json_request(url: str, *, access_token: str) -> dict:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        method="GET",
    )
    return _read_json_response(request)


def _read_json_response(request: Request) -> dict:
    try:
        with urlopen(request, timeout=45) as response:
            body = response.read()
            return json.loads(body.decode("utf-8")) if body else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise QuickBooksUnavailable(
            f"QuickBooks rejected the request ({exc.code}): {_provider_reason(detail)}"
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise QuickBooksUnavailable("QuickBooks is temporarily unreachable.") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise QuickBooksUnavailable("QuickBooks returned an invalid response.") from exc


def _provider_reason(detail: str) -> str:
    try:
        parsed = json.loads(detail)
    except json.JSONDecodeError:
        return "provider_error"
    if isinstance(parsed, dict):
        error = parsed.get("error")
        if isinstance(error, str):
            return error[:120]
        fault = parsed.get("Fault")
        if isinstance(fault, dict):
            errors = fault.get("Error")
            if isinstance(errors, list) and errors and isinstance(errors[0], dict):
                return str(errors[0].get("code") or "provider_error")[:120]
    return "provider_error"


def _token_result(
    result: dict,
    *,
    existing_refresh_token: str | None = None,
) -> QuickBooksTokenResult:
    access_token = result.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise QuickBooksUnavailable("QuickBooks returned no access token.")
    refresh_token = result.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token:
        refresh_token = existing_refresh_token
    if "scope" not in result or result["scope"] is None:
        scopes = [REQUIRED_SCOPE]
    else:
        scopes = [scope for scope in str(result["scope"]).split() if scope]
    if REQUIRED_SCOPE not in scopes:
        raise QuickBooksUnavailable("The required QuickBooks accounting permission was not granted.")
    now = datetime.now(UTC)
    try:
        access_seconds = max(int(result.get("expires_in", 3600)), 60)
    except (TypeError, ValueError):
        access_seconds = 3600
    refresh_expires_at = None
    try:
        refresh_seconds = int(result.get("x_refresh_token_expires_in", 0))
        if refresh_seconds > 0:
            refresh_expires_at = now + timedelta(seconds=refresh_seconds)
    except (TypeError, ValueError):
        refresh_expires_at = None
    return QuickBooksTokenResult(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=now + timedelta(seconds=access_seconds),
        refresh_token_expires_at=refresh_expires_at,
        scopes=scopes,
    )
