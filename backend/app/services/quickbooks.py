from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import base64
import hashlib
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

INTUIT_AUTHORIZATION_URL = "https://appcenter.intuit.com/connect/oauth2"
INTUIT_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
INTUIT_REVOKE_URL = "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"
QUICKBOOKS_SANDBOX_API_URL = "https://sandbox-quickbooks.api.intuit.com"
QUICKBOOKS_PRODUCTION_API_URL = "https://quickbooks.api.intuit.com"
REQUIRED_SCOPE = "com.intuit.quickbooks.accounting"
KNOWN_OAUTH_ERROR_CODES = {
    "invalid_request",
    "invalid_client",
    "invalid_grant",
    "unauthorized_client",
    "unsupported_grant_type",
    "invalid_scope",
}


def provider_error_code(value: str | None) -> str:
    sanitized = _sanitize_diagnostic_value(value)
    return sanitized if sanitized in KNOWN_OAUTH_ERROR_CODES else "provider_error"


class QuickBooksUnavailable(RuntimeError):
    pass


class QuickBooksProviderError(QuickBooksUnavailable):
    def __init__(
        self,
        message: str,
        *,
        reason: str = "provider_error",
        status_code: int | None = None,
        intuit_tid: str | None = None,
        reconnect_required: bool = False,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.status_code = status_code
        self.intuit_tid = intuit_tid
        self.reconnect_required = reconnect_required


@dataclass(frozen=True)
class QuickBooksTokenResult:
    access_token: str
    refresh_token: str | None
    expires_at: datetime
    refresh_token_expires_at: datetime | None
    scopes: list[str]
    intuit_tid: str | None = None


@dataclass(frozen=True)
class QuickBooksCompanyInfo:
    company_name: str
    legal_name: str | None
    intuit_tid: str | None = None


@dataclass(frozen=True)
class QuickBooksProviderResponse:
    payload: dict
    intuit_tid: str | None


@dataclass(frozen=True)
class QuickBooksCredentials:
    client_id: str
    client_secret: str
    token_encryption_key: str


def quickbooks_environment() -> str:
    settings = get_settings()
    environment = settings.quickbooks_environment.strip().lower()
    if environment not in {"sandbox", "production"}:
        raise QuickBooksUnavailable("QuickBooks environment is not supported.")
    if (
        environment == "production"
        and settings.environment.strip().lower() != "production"
    ):
        raise QuickBooksUnavailable(
            "QuickBooks live access is restricted to the protected production deployment."
        )
    return environment


def live_read_only_is_approved(environment: str | None = None) -> bool:
    selected = environment or quickbooks_environment()
    settings = get_settings()
    return selected == "sandbox" or (
        selected == "production"
        and settings.environment.strip().lower() == "production"
        and settings.quickbooks_live_read_only_approved
    )


def environment_credentials() -> QuickBooksCredentials | None:
    settings = get_settings()
    environment = quickbooks_environment()
    if not (
        live_read_only_is_approved(environment)
        and settings.quickbooks_client_id
        and settings.quickbooks_client_secret
        and settings.quickbooks_token_encryption_key
    ):
        return None
    return QuickBooksCredentials(
        client_id=settings.quickbooks_client_id,
        client_secret=settings.quickbooks_client_secret,
        token_encryption_key=settings.quickbooks_token_encryption_key,
    )


def environment_credentials_for_teardown() -> QuickBooksCredentials | None:
    """Return configured credentials for revocation without reopening live OAuth."""
    settings = get_settings()
    quickbooks_environment()
    if not (
        settings.quickbooks_client_id
        and settings.quickbooks_client_secret
        and settings.quickbooks_token_encryption_key
    ):
        return None
    return QuickBooksCredentials(
        client_id=settings.quickbooks_client_id,
        client_secret=settings.quickbooks_client_secret,
        token_encryption_key=settings.quickbooks_token_encryption_key,
    )


def quickbooks_is_configured(credentials: QuickBooksCredentials | None = None) -> bool:
    return bool((credentials or environment_credentials()) and get_settings().quickbooks_redirect_uri)


def authorization_url(state: str, credentials: QuickBooksCredentials | None = None) -> str:
    settings = get_settings()
    environment = quickbooks_environment()
    if not live_read_only_is_approved(environment):
        raise QuickBooksUnavailable("QuickBooks live read-only connection is not approved.")
    credentials = credentials or environment_credentials()
    if not quickbooks_is_configured(credentials) or credentials is None:
        raise QuickBooksUnavailable("QuickBooks OAuth is not configured.")
    return f"{INTUIT_AUTHORIZATION_URL}?{urlencode({
        'client_id': credentials.client_id,
        'redirect_uri': settings.quickbooks_redirect_uri,
        'response_type': 'code',
        'scope': REQUIRED_SCOPE,
        'state': state,
    })}"


def state_digest(state: str) -> str:
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def encrypt_token(token: str, encryption_key: str | None = None) -> str:
    return _token_cipher(encryption_key).encrypt(token.encode("utf-8")).decode("ascii")


def decrypt_token(encrypted_token: str, encryption_key: str | None = None) -> str:
    try:
        return _token_cipher(encryption_key).decrypt(encrypted_token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, UnicodeEncodeError, ValueError) as exc:
        raise QuickBooksUnavailable(
            "The stored QuickBooks connection cannot be decrypted. Reconnect QuickBooks."
        ) from exc


def exchange_authorization_code(
    code: str,
    existing_refresh_token: str | None = None,
    credentials: QuickBooksCredentials | None = None,
) -> QuickBooksTokenResult:
    settings = get_settings()
    response = _form_provider_request(
        INTUIT_TOKEN_URL,
        {
            "code": code,
            "redirect_uri": settings.quickbooks_redirect_uri,
            "grant_type": "authorization_code",
        },
        credentials=credentials,
    )
    return _token_result(
        response.payload,
        existing_refresh_token=existing_refresh_token,
        intuit_tid=response.intuit_tid,
    )


def refresh_access_token(
    refresh_token: str,
    credentials: QuickBooksCredentials | None = None,
) -> QuickBooksTokenResult:
    response = _form_provider_request(
        INTUIT_TOKEN_URL,
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        credentials=credentials,
    )
    return _token_result(
        response.payload,
        existing_refresh_token=refresh_token,
        intuit_tid=response.intuit_tid,
    )


def get_company_info(
    access_token: str,
    realm_id: str,
    environment: str | None = None,
) -> QuickBooksCompanyInfo:
    if not realm_id.isdigit() or len(realm_id) > 64:
        raise QuickBooksUnavailable("QuickBooks returned an invalid company identifier.")
    selected = environment or quickbooks_environment()
    if not live_read_only_is_approved(selected):
        raise QuickBooksUnavailable("QuickBooks live read-only connection is not approved.")
    api_base_url = {
        "sandbox": QUICKBOOKS_SANDBOX_API_URL,
        "production": QUICKBOOKS_PRODUCTION_API_URL,
    }.get(selected)
    if api_base_url is None:
        raise QuickBooksUnavailable("QuickBooks environment is not supported.")
    safe_realm = quote(realm_id, safe="")
    response = _json_provider_request(
        f"{api_base_url}/v3/company/{safe_realm}/companyinfo/{safe_realm}?minorversion=75",
        access_token=access_token,
    )
    payload = response.payload
    raw = payload.get("CompanyInfo")
    if not isinstance(raw, dict) or not raw.get("CompanyName"):
        raise QuickBooksUnavailable("QuickBooks returned no company identity.")
    legal_name = raw.get("LegalName")
    return QuickBooksCompanyInfo(
        company_name=str(raw["CompanyName"])[:255],
        legal_name=str(legal_name)[:255] if legal_name else None,
        intuit_tid=response.intuit_tid,
    )


def revoke_token(token: str, credentials: QuickBooksCredentials | None = None) -> None:
    request = Request(
        INTUIT_REVOKE_URL,
        data=json.dumps({"token": token}).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Authorization": _basic_authorization(credentials),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    _read_json_response(request)


def encrypt_configuration_secret(value: str) -> str:
    return _configuration_cipher().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_configuration_secret(value: str) -> str:
    try:
        return _configuration_cipher().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, UnicodeEncodeError, ValueError) as exc:
        raise QuickBooksUnavailable(
            "The stored QuickBooks configuration cannot be decrypted. Remove and configure it again."
        ) from exc


def _configuration_cipher() -> Fernet:
    source = get_settings().secret_key
    digest = hashlib.sha256(b"ihos-quickbooks-configuration-v1\0" + source.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _token_cipher(encryption_key: str | None = None) -> Fernet:
    source = encryption_key or get_settings().quickbooks_token_encryption_key
    if not source:
        raise QuickBooksUnavailable("QuickBooks token encryption is not configured.")
    key = base64.urlsafe_b64encode(hashlib.sha256(source.encode("utf-8")).digest())
    return Fernet(key)


def _basic_authorization(credentials: QuickBooksCredentials | None = None) -> str:
    credentials = credentials or environment_credentials()
    if credentials is None:
        raise QuickBooksUnavailable("QuickBooks OAuth is not configured.")
    encoded = base64.b64encode(
        f"{credentials.client_id}:{credentials.client_secret}".encode("utf-8")
    ).decode("ascii")
    return f"Basic {encoded}"


def _form_request(
    url: str,
    fields: dict[str, str],
    *,
    credentials: QuickBooksCredentials | None = None,
) -> dict:
    return _form_provider_request(url, fields, credentials=credentials).payload


def _form_provider_request(
    url: str,
    fields: dict[str, str],
    *,
    credentials: QuickBooksCredentials | None = None,
) -> QuickBooksProviderResponse:
    request = Request(
        url,
        data=urlencode(fields).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Authorization": _basic_authorization(credentials),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    return _read_provider_response(request)


def _json_request(url: str, *, access_token: str) -> dict:
    return _json_provider_request(url, access_token=access_token).payload


def _json_provider_request(url: str, *, access_token: str) -> QuickBooksProviderResponse:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        method="GET",
    )
    return _read_provider_response(request)


def _read_json_response(request: Request) -> dict:
    return _read_provider_response(request).payload


def _read_provider_response(request: Request) -> QuickBooksProviderResponse:
    try:
        with urlopen(request, timeout=45) as response:
            body = response.read()
            payload = json.loads(body.decode("utf-8")) if body else {}
            if not isinstance(payload, dict):
                raise QuickBooksUnavailable("QuickBooks returned an invalid response.")
            return QuickBooksProviderResponse(
                payload=payload,
                intuit_tid=_sanitize_diagnostic_value(_header_value(response.headers, "intuit_tid")),
            )
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        reason = _provider_reason(detail)
        reconnect_required = reason in {
            "invalid_grant",
            "invalid_client",
            "unauthorized_client",
        }
        raise QuickBooksProviderError(
            "QuickBooks authorization must be renewed."
            if reconnect_required
            else "QuickBooks rejected the request.",
            reason=reason,
            status_code=exc.code,
            intuit_tid=_sanitize_diagnostic_value(_header_value(exc.headers, "intuit_tid")),
            reconnect_required=reconnect_required,
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise QuickBooksProviderError(
            "QuickBooks is temporarily unreachable.",
            reason="provider_unreachable",
        ) from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise QuickBooksProviderError(
            "QuickBooks returned an invalid response.",
            reason="invalid_provider_response",
        ) from exc


def _provider_reason(detail: str) -> str:
    try:
        parsed = json.loads(detail)
    except json.JSONDecodeError:
        return "provider_error"
    if isinstance(parsed, dict):
        error = parsed.get("error")
        if isinstance(error, str):
            return provider_error_code(error)
        fault = parsed.get("Fault")
        if isinstance(fault, dict):
            errors = fault.get("Error")
            if isinstance(errors, list) and errors and isinstance(errors[0], dict):
                sanitized = _sanitize_diagnostic_value(
                    str(errors[0].get("code") or "provider_error")
                )
                return sanitized if sanitized and sanitized.isdigit() else "provider_error"
    return "provider_error"


def _sanitize_diagnostic_value(value: str | None) -> str | None:
    if not value:
        return None
    sanitized = re.sub(r"[^A-Za-z0-9._:-]", "_", str(value))[:120]
    return sanitized or None


def _header_value(headers: object, name: str) -> str | None:
    getter = getattr(headers, "get", None)
    value = getter(name) if callable(getter) else None
    return str(value) if value is not None else None


def _token_result(
    result: dict,
    *,
    existing_refresh_token: str | None = None,
    intuit_tid: str | None = None,
) -> QuickBooksTokenResult:
    access_token = result.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise QuickBooksUnavailable("QuickBooks returned no access token.")
    refresh_token = result.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token:
        refresh_token = existing_refresh_token
    if "scope" not in result:
        scopes = [REQUIRED_SCOPE]
    else:
        raw_scope = result["scope"]
        if not isinstance(raw_scope, str):
            raise QuickBooksUnavailable(
                "QuickBooks returned an invalid permission response."
            )
        scopes = [scope for scope in raw_scope.split() if scope]
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
        intuit_tid=_sanitize_diagnostic_value(intuit_tid),
    )
