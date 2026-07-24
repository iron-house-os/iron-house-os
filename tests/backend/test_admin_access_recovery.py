import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.user import Employee, LoginThrottle, UserAccount
from app.services.admin_access_recovery import (
    AdminAccessRecoveryBlocked,
    inspect_admin_recovery,
    inspect_identity_cutover,
    recover_admin_access,
)
from app.services.auth import hash_password, login_subject_hash, verify_password
from app.services.email_domain_migration import (
    CANONICAL_EMAIL_DOMAIN,
    LEGACY_EMAIL_DOMAIN,
    migrate_email_domain,
)


def _email(local_part: str, domain: str = CANONICAL_EMAIL_DOMAIN) -> str:
    return f"{local_part}@{domain}"


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _admin(
    *,
    email: str | None = None,
    role: str = "admin",
    is_active: bool = True,
    password_reset_required: bool = False,
) -> UserAccount:
    return UserAccount(
        email=email or _email("jeremie"),
        display_name="Jeremie Peters",
        role=role,
        password_hash=hash_password("existing-admin-password"),
        is_active=is_active,
        session_version=3,
        password_reset_required=password_reset_required,
    )


def test_admin_recovery_inspection_returns_safe_account_confirmation() -> None:
    with _session() as db:
        account = _admin()
        db.add(account)
        db.commit()

        result = inspect_admin_recovery(db, account.email)
        rendered = json.dumps(result.to_dict())

        assert result.eligible is True
        assert result.account_id == str(account.id)
        assert result.active_admin_count == 1
        assert "existing-admin-password" not in rendered
        assert "password_hash" not in rendered


def test_admin_recovery_resets_password_invalidates_sessions_and_clears_throttle() -> None:
    with _session() as db:
        account = _admin()
        db.add(account)
        db.flush()
        db.add(
            LoginThrottle(
                key_hash=login_subject_hash(account.email),
                failed_attempts=5,
            )
        )
        db.commit()

        evidence = recover_admin_access(
            db,
            email=account.email,
            confirm_account_id=str(account.id),
            new_password="temporary-admin-password",
            reason="Business account migration access loss",
            operator="Jeremie Peters",
        )
        db.commit()
        recovered = db.get(UserAccount, account.id)

        assert recovered is not None
        assert verify_password("temporary-admin-password", recovered.password_hash)
        assert recovered.session_version == 4
        assert recovered.password_reset_required is True
        assert evidence.previous_session_version == 3
        assert evidence.new_session_version == 4
        assert evidence.login_throttles_cleared == 1
        assert db.scalars(select(LoginThrottle)).all() == []
        rendered = json.dumps(evidence.to_dict())
        assert "temporary-admin-password" not in rendered
        assert "password_hash" not in rendered


@pytest.mark.parametrize(
    ("account", "confirmed_id", "reason", "issue"),
    [
        (_admin(role="viewer"), None, "Business access recovery", "not an administrator"),
        (_admin(is_active=False), None, "Business access recovery", "inactive"),
        (
            _admin(email=_email("jeremie", LEGACY_EMAIL_DOMAIN)),
            None,
            "Business access recovery",
            "canonical company email domain",
        ),
        (_admin(), "00000000-0000-0000-0000-000000000999", "Business access recovery", "does not match"),
        (_admin(), None, "short", "at least 10 characters"),
    ],
)
def test_admin_recovery_refuses_unsafe_targets(
    account: UserAccount,
    confirmed_id: str | None,
    reason: str,
    issue: str,
) -> None:
    with _session() as db:
        db.add(account)
        db.commit()

        with pytest.raises(AdminAccessRecoveryBlocked, match=issue):
            recover_admin_access(
                db,
                email=account.email,
                confirm_account_id=confirmed_id or str(account.id),
                new_password="temporary-admin-password",
                reason=reason,
                operator="Jeremie Peters",
            )
        db.rollback()
        unchanged = db.get(UserAccount, account.id)
        assert unchanged is not None
        assert unchanged.session_version == 3
        assert verify_password("existing-admin-password", unchanged.password_hash)


def test_admin_recovery_refuses_password_reuse() -> None:
    with _session() as db:
        account = _admin()
        db.add(account)
        db.commit()

        with pytest.raises(AdminAccessRecoveryBlocked, match="must differ"):
            recover_admin_access(
                db,
                email=account.email,
                confirm_account_id=str(account.id),
                new_password="existing-admin-password",
                reason="Business account migration access loss",
                operator="Jeremie Peters",
            )


def test_identity_cutover_readiness_tracks_migration_and_password_change() -> None:
    with _session() as db:
        account = _admin(password_reset_required=True)
        employee = Employee(
            first_name="Jeremie",
            last_name="Peters",
            email=_email("jeremie", LEGACY_EMAIL_DOMAIN),
            status="active",
            portal_role="employee",
        )
        db.add_all([account, employee])
        db.commit()

        blocked = inspect_identity_cutover(
            db,
            canonical_admin_email=account.email,
            configured_bootstrap_email=account.email,
        )
        assert blocked.ready is False
        assert blocked.pending_identity_changes == 1
        assert any("forced password change" in issue for issue in blocked.issues)

        migrate_email_domain(db, apply=True)
        account.password_reset_required = False
        db.commit()
        ready = inspect_identity_cutover(
            db,
            canonical_admin_email=account.email,
            configured_bootstrap_email=account.email,
        )
        assert ready.ready is True
        assert ready.pending_identity_changes == 0
        assert ready.issues == ()
