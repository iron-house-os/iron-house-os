from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import UserAccount
from app.schemas.identity_governance import (
    IdentityGovernanceAccount,
    IdentityGovernanceFinding,
    IdentityGovernanceSnapshot,
    IdentityGovernanceSummary,
)
from app.services.email_domain_migration import CANONICAL_EMAIL_DOMAIN, LEGACY_EMAIL_DOMAIN


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def build_identity_governance_snapshot(
    db: Session,
    *,
    now: datetime | None = None,
) -> IdentityGovernanceSnapshot:
    generated_at = _utc(now) or datetime.now(timezone.utc)
    accounts = list(db.scalars(select(UserAccount).order_by(UserAccount.email)))
    reasons: dict[object, list[str]] = {account.id: [] for account in accounts}
    findings: list[IdentityGovernanceFinding] = []

    def add_finding(
        code: str,
        severity: str,
        title: str,
        recommendation: str,
        affected: list[UserAccount],
        reason: str,
    ) -> None:
        if not affected:
            return
        for account in affected:
            reasons[account.id].append(reason)
        findings.append(
            IdentityGovernanceFinding(
                code=code,
                severity=severity,
                title=title,
                recommendation=recommendation,
                account_ids=[account.id for account in affected],
            )
        )

    active_admins = [account for account in accounts if account.is_active and account.role == "admin"]
    if not active_admins:
        findings.append(
            IdentityGovernanceFinding(
                code="no_active_administrator",
                severity="critical",
                title="No active administrator account",
                recommendation="Recover and verify an administrator account before further access changes.",
                account_ids=[],
            )
        )
    elif len(active_admins) == 1:
        add_finding(
            "single_active_administrator",
            "high",
            "Single active administrator",
            "Approve and provision a second named administrator to remove the access single point of failure.",
            active_admins,
            "Only active administrator",
        )

    legacy = [account for account in accounts if account.email.lower().endswith(f"@{LEGACY_EMAIL_DOMAIN}")]
    add_finding(
        "legacy_email_domain",
        "critical",
        "Legacy company email domain remains",
        f"Migrate the affected account to @{CANONICAL_EMAIL_DOMAIN} and invalidate its sessions.",
        legacy,
        "Legacy email domain",
    )

    noncanonical = [
        account
        for account in accounts
        if not account.email.lower().endswith(f"@{CANONICAL_EMAIL_DOMAIN}") and account not in legacy
    ]
    add_finding(
        "noncanonical_email_domain",
        "high",
        "Account uses a non-canonical email domain",
        "Confirm the business reason and document approval, or move the account to the company domain.",
        noncanonical,
        "Non-canonical email domain",
    )

    pending_reset = [account for account in accounts if account.is_active and account.password_reset_required]
    add_finding(
        "password_change_pending",
        "high",
        "Temporary password change is pending",
        "Have the named user sign in and replace the temporary password.",
        pending_reset,
        "Password change pending",
    )

    never_used = [
        account
        for account in accounts
        if account.is_active
        and account.last_login_at is None
        and _utc(account.created_at)
        and generated_at - _utc(account.created_at) >= timedelta(days=7)
    ]
    add_finding(
        "never_used_account",
        "normal",
        "Active account has never signed in",
        "Confirm the account is still required; deactivate it if onboarding is no longer proceeding.",
        never_used,
        "Never signed in",
    )

    stale = [
        account
        for account in accounts
        if account.is_active
        and _utc(account.last_login_at)
        and generated_at - _utc(account.last_login_at) >= timedelta(days=90)
    ]
    add_finding(
        "stale_account",
        "high",
        "Active account has been unused for 90 days",
        "Confirm access with the account owner and deactivate access that is no longer required.",
        stale,
        "No sign-in for 90 days",
    )

    by_email: dict[str, list[UserAccount]] = defaultdict(list)
    for account in accounts:
        by_email[account.email.casefold()].append(account)
    duplicates = [group for group in by_email.values() if len(group) > 1]
    for index, group in enumerate(duplicates, start=1):
        add_finding(
            f"duplicate_identity_{index}",
            "critical",
            "Case-insensitive duplicate identity",
            "Freeze account changes and reconcile the duplicate records before migration or recovery.",
            group,
            "Duplicate identity",
        )

    governed_accounts = [
        IdentityGovernanceAccount(
            id=account.id,
            email=account.email,
            display_name=account.display_name,
            role=account.role,
            is_active=account.is_active,
            last_login_at=_utc(account.last_login_at),
            password_reset_required=account.password_reset_required,
            review_reasons=reasons[account.id],
        )
        for account in accounts
    ]
    return IdentityGovernanceSnapshot(
        generated_at=generated_at,
        canonical_email_domain=CANONICAL_EMAIL_DOMAIN,
        summary=IdentityGovernanceSummary(
            total_accounts=len(accounts),
            active_accounts=sum(account.is_active for account in accounts),
            active_administrators=len(active_admins),
            legacy_domain_accounts=len(legacy),
            accounts_requiring_review=sum(bool(account.review_reasons) for account in governed_accounts),
            critical_findings=sum(finding.severity == "critical" for finding in findings),
        ),
        accounts=governed_accounts,
        findings=sorted(findings, key=lambda finding: {"critical": 0, "high": 1, "normal": 2}[finding.severity]),
    )
