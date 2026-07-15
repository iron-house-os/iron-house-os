from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
import hashlib
import hmac
import secrets
from uuid import UUID

from jose import JWTError, jwt
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import LoginThrottle, UserAccount
from app.schemas.auth import UserAccountCreate, UserAccountUpdate

PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 600_000
SESSION_ALGORITHM = "HS256"
SESSION_AUDIENCE = "iron-house-os"
SESSION_ISSUER = "iron-house-os-api"
ALLOWED_ROLES = {"admin", "operations_manager", "estimator", "viewer"}


@dataclass(frozen=True)
class AuthenticatedUser:
    id: UUID
    email: str
    display_name: str
    role: str
    session_version: int
    password_reset_required: bool = False


class AuthenticationStatus(StrEnum):
    AUTHENTICATED = "authenticated"
    INVALID = "invalid"
    LOCKED = "locked"


@dataclass(frozen=True)
class AuthenticationResult:
    status: AuthenticationStatus
    subject_hash: str
    account: UserAccount | None = None
    locked_until: datetime | None = None


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Passwords must be at least 12 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    encoded_salt = urlsafe_b64encode(salt).decode().rstrip("=")
    encoded_digest = urlsafe_b64encode(digest).decode().rstrip("=")
    return f"{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}${encoded_salt}${encoded_digest}"


def _decode_base64(value: str) -> bytes:
    return urlsafe_b64decode(value + "=" * (-len(value) % 4))


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, raw_iterations, raw_salt, raw_digest = encoded.split("$", 3)
        if algorithm != PASSWORD_ALGORITHM:
            return False
        iterations = int(raw_iterations)
        if iterations < 100_000 or iterations > PASSWORD_ITERATIONS:
            return False
        expected = _decode_base64(raw_digest)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            _decode_base64(raw_salt),
            iterations,
        )
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(actual, expected)


DUMMY_PASSWORD_HASH = hash_password("not-a-real-iron-house-password")


def login_subject_hash(email: str) -> str:
    return hashlib.sha256(normalize_email(email).encode()).hexdigest()


def _utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def create_session_token(account: UserAccount) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {
            "sub": str(account.id),
            "email": account.email,
            "role": account.role,
            "sv": account.session_version,
            "iat": now,
            "exp": expires_at,
            "iss": SESSION_ISSUER,
            "aud": SESSION_AUDIENCE,
            "jti": secrets.token_urlsafe(16),
        },
        settings.secret_key,
        algorithm=SESSION_ALGORITHM,
    )


def decode_session_token(token: str) -> dict[str, object]:
    try:
        return jwt.decode(
            token,
            get_settings().secret_key,
            algorithms=[SESSION_ALGORITHM],
            audience=SESSION_AUDIENCE,
            issuer=SESSION_ISSUER,
        )
    except JWTError as exc:
        raise ValueError("Invalid or expired session.") from exc


def account_to_principal(account: UserAccount) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=account.id,
        email=account.email,
        display_name=account.display_name,
        role=account.role,
        session_version=account.session_version,
        password_reset_required=account.password_reset_required,
    )


def authenticate(db: Session, email: str, password: str) -> AuthenticationResult:
    normalized_email = normalize_email(email)
    subject_hash = login_subject_hash(normalized_email)
    now = datetime.now(UTC)
    throttle = db.scalar(
        select(LoginThrottle)
        .where(LoginThrottle.key_hash == subject_hash)
        .with_for_update()
    )
    locked_until = _utc(throttle.locked_until) if throttle is not None else None
    if locked_until is not None and locked_until > now:
        return AuthenticationResult(
            status=AuthenticationStatus.LOCKED,
            subject_hash=subject_hash,
            locked_until=locked_until,
        )
    if throttle is not None and throttle.locked_until is not None:
        throttle.failed_attempts = 0
        throttle.locked_until = None

    account = db.scalar(select(UserAccount).where(func.lower(UserAccount.email) == normalized_email))
    password_matches = verify_password(
        password,
        account.password_hash if account is not None else DUMMY_PASSWORD_HASH,
    )
    if account is None or not account.is_active or not password_matches:
        if throttle is None:
            throttle = LoginThrottle(key_hash=subject_hash, failed_attempts=0)
        throttle.failed_attempts += 1
        throttle.last_failed_at = now
        settings = get_settings()
        status = AuthenticationStatus.INVALID
        if throttle.failed_attempts >= settings.login_max_failed_attempts:
            throttle.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
            status = AuthenticationStatus.LOCKED
        db.add(throttle)
        db.commit()
        return AuthenticationResult(
            status=status,
            subject_hash=subject_hash,
            locked_until=_utc(throttle.locked_until),
        )

    if throttle is not None:
        db.delete(throttle)
    account.last_login_at = datetime.now(UTC)
    db.add(account)
    db.commit()
    db.refresh(account)
    return AuthenticationResult(
        status=AuthenticationStatus.AUTHENTICATED,
        subject_hash=subject_hash,
        account=account,
    )


def get_account(db: Session, account_id: UUID) -> UserAccount | None:
    return db.get(UserAccount, account_id)


def list_accounts(db: Session) -> list[UserAccount]:
    return list(db.scalars(select(UserAccount).order_by(UserAccount.display_name, UserAccount.email)))


def create_account(db: Session, payload: UserAccountCreate) -> UserAccount:
    email = normalize_email(str(payload.email))
    if db.scalar(select(UserAccount.id).where(func.lower(UserAccount.email) == email)) is not None:
        raise ValueError("A user with that email already exists.")
    account = UserAccount(
        email=email,
        display_name=payload.display_name,
        role=payload.role,
        password_hash=hash_password(payload.password),
        is_active=True,
        session_version=1,
        password_reset_required=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def update_account(
    db: Session,
    account: UserAccount,
    payload: UserAccountUpdate,
    *,
    acting_user: AuthenticatedUser,
) -> UserAccount:
    changes = payload.model_dump(exclude_unset=True)
    previous_email = account.email
    if "email" in changes:
        if changes["email"] is None:
            raise ValueError("Email cannot be blank.")
        email = normalize_email(str(changes["email"]))
        duplicate = db.scalar(
            select(UserAccount.id).where(
                func.lower(UserAccount.email) == email,
                UserAccount.id != account.id,
            )
        )
        if duplicate is not None:
            raise ValueError("A user with that email already exists.")
        changes["email"] = email
    if account.id == acting_user.id and changes.get("is_active") is False:
        raise ValueError("You cannot deactivate your own account.")
    if account.id == acting_user.id and changes.get("role") not in (None, "admin"):
        raise ValueError("You cannot remove your own administrator role.")
    would_remove_active_admin = account.role == "admin" and account.is_active and (
        changes.get("role", account.role) != "admin"
        or changes.get("is_active", account.is_active) is False
    )
    if would_remove_active_admin:
        active_admins = db.scalar(
            select(func.count(UserAccount.id)).where(
                UserAccount.role == "admin",
                UserAccount.is_active.is_(True),
            )
        )
        if active_admins is None or active_admins <= 1:
            raise ValueError("At least one active administrator account is required.")
    previous_role = account.role
    previous_active = account.is_active
    for field, value in changes.items():
        setattr(account, field, value)
    if account.role not in ALLOWED_ROLES:
        raise ValueError("Unsupported user role.")
    if (
        account.email != previous_email
        or account.role != previous_role
        or account.is_active != previous_active
    ):
        account.session_version += 1
    if account.email != previous_email:
        clear_login_throttle(db, previous_email)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def clear_login_throttle(db: Session, email: str) -> None:
    throttle = db.scalar(
        select(LoginThrottle).where(LoginThrottle.key_hash == login_subject_hash(email))
    )
    if throttle is not None:
        db.delete(throttle)


def begin_admin_recovery(db: Session, account: UserAccount, password: str) -> UserAccount:
    account.password_hash = hash_password(password)
    account.session_version += 1
    account.password_reset_required = True
    clear_login_throttle(db, account.email)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def change_password(
    db: Session,
    account: UserAccount,
    *,
    current_password: str,
    new_password: str,
) -> UserAccount:
    if not verify_password(current_password, account.password_hash):
        raise ValueError("Current password is incorrect.")
    if verify_password(new_password, account.password_hash):
        raise ValueError("New password must be different from the current password.")
    account.password_hash = hash_password(new_password)
    account.password_reset_required = False
    account.session_version += 1
    clear_login_throttle(db, account.email)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def reset_password(db: Session, account: UserAccount, password: str) -> UserAccount:
    return begin_admin_recovery(db, account, password)
