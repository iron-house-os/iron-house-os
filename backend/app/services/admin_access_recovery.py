from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.user import LoginThrottle, UserAccount
from app.services.auth import hash_password, login_subject_hash, normalize_email, verify_password
from app.services.email_domain_migration import (
    CANONICAL_EMAIL_DOMAIN,
    migrate_email_domain,
)


class AdminAccessRecoveryBlocked(ValueError):
    def __init__(self, issues: list[str]) -> None:
        self.issues = tuple(issues)
        super().__init__("Administrator access recovery blocked: " + "; ".join(issues))


@dataclass(frozen=True)
class AdminRecoveryInspection:
    account_id: str
    email: str
    display_name: str
    role: str
    is_active: bool
    password_reset_required: bool
    session_version: int
    last_login_at: str | None
    active_admin_count: int
    eligible: bool
    issues: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AdminRecoveryEvidence:
    recovery_id: str
    occurred_at: str
    account_id: str
    email: str
    display_name: str
    reason: str
    operator: str
    previous_session_version: int
    new_session_version: int
    password_reset_required: bool
    sessions_invalidated: bool
    login_throttles_cleared: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IdentityCutoverReadiness:
    checked_at: str
    canonical_admin_email: str
    configured_bootstrap_email: str | None
    pending_identity_changes: int
    canonical_admin_found: bool
    canonical_admin_active: bool
    canonical_admin_role: bool
    password_change_complete: bool
    ready: bool
    issues: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_account(db: Session, email: str, *, lock: bool) -> UserAccount:
    normalised = normalize_email(email)
    statement = select(UserAccount).where(func.lower(UserAccount.email) == normalised)
    if lock:
        statement = statement.with_for_update()
    accounts = list(db.scalars(statement))
    if not accounts:
        raise AdminAccessRecoveryBlocked(["No account matches the supplied email."])
    if len(accounts) > 1:
        raise AdminAccessRecoveryBlocked(["Multiple accounts match the supplied email case-insensitively."])
    return accounts[0]


def inspect_admin_recovery(db: Session, email: str, *, lock: bool = False) -> AdminRecoveryInspection:
    account = _load_account(db, email, lock=lock)
    issues: list[str] = []
    domain = account.email.rsplit("@", 1)[-1].casefold()
    if domain != CANONICAL_EMAIL_DOMAIN:
        issues.append("The account does not use the canonical company email domain.")
    if account.role != "admin":
        issues.append("The account is not an administrator.")
    if not account.is_active:
        issues.append("The account is inactive.")
    active_admin_count = int(
        db.scalar(
            select(func.count(UserAccount.id)).where(
                UserAccount.role == "admin",
                UserAccount.is_active.is_(True),
            )
        )
        or 0
    )
    return AdminRecoveryInspection(
        account_id=str(account.id),
        email=account.email,
        display_name=account.display_name,
        role=account.role,
        is_active=account.is_active,
        password_reset_required=account.password_reset_required,
        session_version=account.session_version,
        last_login_at=account.last_login_at.isoformat() if account.last_login_at else None,
        active_admin_count=active_admin_count,
        eligible=not issues,
        issues=tuple(issues),
    )


def recover_admin_access(
    db: Session,
    *,
    email: str,
    confirm_account_id: str,
    new_password: str,
    reason: str,
    operator: str,
) -> AdminRecoveryEvidence:
    inspection = inspect_admin_recovery(db, email, lock=True)
    if not inspection.eligible:
        raise AdminAccessRecoveryBlocked(list(inspection.issues))
    try:
        confirmed_id = UUID(confirm_account_id)
    except ValueError as exc:
        raise AdminAccessRecoveryBlocked(["The confirmed account ID is not a valid UUID."]) from exc
    if str(confirmed_id) != inspection.account_id:
        raise AdminAccessRecoveryBlocked(["The confirmed account ID does not match the account."])
    cleaned_reason = reason.strip()
    if len(cleaned_reason) < 10:
        raise AdminAccessRecoveryBlocked(["A recovery reason of at least 10 characters is required."])
    cleaned_operator = operator.strip()
    if not cleaned_operator:
        raise AdminAccessRecoveryBlocked(["The recovery operator is required."])

    account = db.get(UserAccount, confirmed_id)
    if account is None:
        raise AdminAccessRecoveryBlocked(["The account no longer exists."])
    if verify_password(new_password, account.password_hash):
        raise AdminAccessRecoveryBlocked(["The temporary password must differ from the existing password."])
    new_password_hash = hash_password(new_password)
    previous_session_version = account.session_version
    account.password_hash = new_password_hash
    account.session_version += 1
    account.password_reset_required = True

    throttle_result = db.execute(
        delete(LoginThrottle).where(LoginThrottle.key_hash == login_subject_hash(account.email))
    )
    db.flush()
    return AdminRecoveryEvidence(
        recovery_id=str(uuid4()),
        occurred_at=datetime.now(UTC).isoformat(),
        account_id=str(account.id),
        email=account.email,
        display_name=account.display_name,
        reason=cleaned_reason,
        operator=cleaned_operator,
        previous_session_version=previous_session_version,
        new_session_version=account.session_version,
        password_reset_required=account.password_reset_required,
        sessions_invalidated=True,
        login_throttles_cleared=int(throttle_result.rowcount or 0),
    )


def inspect_identity_cutover(
    db: Session,
    *,
    canonical_admin_email: str,
    configured_bootstrap_email: str | None,
) -> IdentityCutoverReadiness:
    admin_email = normalize_email(canonical_admin_email)
    issues: list[str] = []
    migration = migrate_email_domain(db)
    pending_changes = len(migration.changes)
    if pending_changes:
        issues.append(f"{pending_changes} active identity or routing values still require migration.")

    configured_email = normalize_email(configured_bootstrap_email) if configured_bootstrap_email else None
    if configured_email is None:
        issues.append("BOOTSTRAP_ADMIN_EMAIL is not configured.")
    elif configured_email != admin_email:
        issues.append("BOOTSTRAP_ADMIN_EMAIL does not match the canonical administrator.")

    account: UserAccount | None
    try:
        account = _load_account(db, admin_email, lock=False)
    except AdminAccessRecoveryBlocked as exc:
        account = None
        issues.extend(exc.issues)

    admin_found = account is not None
    admin_active = bool(account and account.is_active)
    admin_role = bool(account and account.role == "admin")
    password_change_complete = bool(account and not account.password_reset_required)
    if account is not None:
        if not admin_active:
            issues.append("The canonical administrator account is inactive.")
        if not admin_role:
            issues.append("The canonical administrator account does not have the admin role.")
        if not password_change_complete:
            issues.append("The canonical administrator must complete the forced password change.")

    return IdentityCutoverReadiness(
        checked_at=datetime.now(UTC).isoformat(),
        canonical_admin_email=admin_email,
        configured_bootstrap_email=configured_email,
        pending_identity_changes=pending_changes,
        canonical_admin_found=admin_found,
        canonical_admin_active=admin_active,
        canonical_admin_role=admin_role,
        password_change_complete=password_change_complete,
        ready=not issues,
        issues=tuple(issues),
    )
