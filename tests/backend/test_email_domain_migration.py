from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.bootstrap_admin import validate_bootstrap_admin_email
from app.models.contact import Contact
from app.models.field_operations import FieldRecord
from app.models.finance import StartupExpense
from app.models.rfq import RFQPackage
from app.models.supplier import Supplier
from app.models.user import Employee, LoginThrottle, UserAccount
from app.services.auth import hash_password, login_subject_hash
from app.services.email_domain_migration import (
    CANONICAL_EMAIL_DOMAIN,
    EmailDomainMigrationConflict,
    LEGACY_EMAIL_DOMAIN,
    migrate_email_domain,
)


def _email(local_part: str, domain: str) -> str:
    return f"{local_part}@{domain}"


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _seed_operational_records(db: Session) -> dict[str, object]:
    legacy_admin = _email("jeremie", LEGACY_EMAIL_DOMAIN)
    canonical_admin = _email("jeremie", CANONICAL_EMAIL_DOMAIN)
    supplier = Supplier(
        name="Domain Migration Supplier",
        metadata_json={"email": _email("estimating", LEGACY_EMAIL_DOMAIN), "status": "preferred"},
    )
    db.add(supplier)
    db.flush()
    account = UserAccount(
        email=legacy_admin,
        display_name="Jeremie Peters",
        role="admin",
        password_hash=hash_password("build-231-test-password"),
        is_active=True,
        session_version=4,
    )
    employee = Employee(
        first_name="Jeremie",
        last_name="Peters",
        email=_email("Jeremie", LEGACY_EMAIL_DOMAIN.upper()),
        status="active",
        portal_role="employee",
    )
    contact = Contact(
        supplier_id=supplier.id,
        first_name="Estimator",
        email=_email("quotes", LEGACY_EMAIL_DOMAIN),
    )
    package = RFQPackage(
        title="Build 231 routing test",
        status="draft",
        supplier_category_targets=[],
        metadata_json={
            "supplier_contacts": {"supplier-1": {"recipient_email": _email("quotes", LEGACY_EMAIL_DOMAIN)}},
            "gmail_drive_workflow": {
                "sender": {"email": legacy_admin},
                "gmail_drafts": [
                    {
                        "to": _email("quotes", LEGACY_EMAIL_DOMAIN),
                        "body": f"Reply to {legacy_admin}.\n\nThank you.",
                    }
                ],
            },
        },
    )
    field_record = FieldRecord(
        record_type="issue",
        work_date=date(2026, 7, 24),
        title="Build 231 routing test",
        alert_recipients=[legacy_admin, "Mac Warren"],
        status="submitted",
        severity="medium",
        details={},
        document_ids=[],
        signatures=[{"signed_by_account": legacy_admin}],
        submitted_by=legacy_admin,
    )
    expense = StartupExpense(
        expense_date=date(2026, 7, 1),
        vendor_name="Historical Vendor",
        description="Historical evidence",
        amount=100,
        category="legal",
        source_email=legacy_admin,
        funding_source="owner_loan",
        tax_treatment="needs_review",
        status="review",
        receipt_metadata={},
        created_by=legacy_admin,
    )
    db.add_all(
        [
            account,
            employee,
            contact,
            package,
            field_record,
            expense,
            LoginThrottle(key_hash=login_subject_hash(legacy_admin), failed_attempts=2),
            LoginThrottle(key_hash=login_subject_hash(canonical_admin), failed_attempts=1),
        ]
    )
    db.commit()
    return {
        "account": account,
        "employee": employee,
        "contact": contact,
        "supplier": supplier,
        "package": package,
        "field_record": field_record,
        "expense": expense,
        "legacy_admin": legacy_admin,
        "canonical_admin": canonical_admin,
    }


def test_email_domain_migration_dry_run_has_no_writes() -> None:
    with _session() as db:
        seeded = _seed_operational_records(db)
        report = migrate_email_domain(db)
        assert report.applied is False
        assert len(report.changes) == 9
        assert report.sessions_invalidated == 0
        assert db.get(UserAccount, seeded["account"].id).email == seeded["legacy_admin"]
        assert len(db.scalars(select(LoginThrottle)).all()) == 2


def test_email_domain_migration_updates_active_routing_and_preserves_history() -> None:
    with _session() as db:
        seeded = _seed_operational_records(db)
        report = migrate_email_domain(db, apply=True)
        db.commit()

        account = db.get(UserAccount, seeded["account"].id)
        employee = db.get(Employee, seeded["employee"].id)
        contact = db.get(Contact, seeded["contact"].id)
        supplier = db.get(Supplier, seeded["supplier"].id)
        package = db.get(RFQPackage, seeded["package"].id)
        field_record = db.get(FieldRecord, seeded["field_record"].id)
        expense = db.get(StartupExpense, seeded["expense"].id)

        assert report.sessions_invalidated == 1
        assert report.login_throttles_cleared == 2
        assert account.email == seeded["canonical_admin"]
        assert account.session_version == 5
        assert employee.email == _email("jeremie", CANONICAL_EMAIL_DOMAIN)
        assert contact.email == _email("quotes", CANONICAL_EMAIL_DOMAIN)
        assert supplier.metadata_json["email"] == _email("estimating", CANONICAL_EMAIL_DOMAIN)
        assert package.metadata_json["supplier_contacts"]["supplier-1"]["recipient_email"] == _email(
            "quotes", CANONICAL_EMAIL_DOMAIN
        )
        workflow = package.metadata_json["gmail_drive_workflow"]
        assert workflow["sender"]["email"] == seeded["canonical_admin"]
        assert workflow["gmail_drafts"][0]["to"] == _email("quotes", CANONICAL_EMAIL_DOMAIN)
        assert workflow["gmail_drafts"][0]["body"] == (f"Reply to {seeded['canonical_admin']}.\n\nThank you.")
        assert field_record.alert_recipients == [seeded["canonical_admin"], "Mac Warren"]
        assert field_record.submitted_by == seeded["legacy_admin"]
        assert field_record.signatures[0]["signed_by_account"] == seeded["legacy_admin"]
        assert expense.source_email == seeded["legacy_admin"]
        assert expense.created_by == seeded["legacy_admin"]
        assert db.scalars(select(LoginThrottle)).all() == []

        second = migrate_email_domain(db, apply=True)
        assert second.changes == ()
        assert second.sessions_invalidated == 0


def test_email_domain_migration_refuses_case_insensitive_collisions() -> None:
    with _session() as db:
        db.add_all(
            [
                UserAccount(
                    email=_email("owner", LEGACY_EMAIL_DOMAIN),
                    display_name="Legacy Owner",
                    role="admin",
                    password_hash=hash_password("build-231-test-password"),
                    is_active=True,
                ),
                UserAccount(
                    email=_email("OWNER", CANONICAL_EMAIL_DOMAIN),
                    display_name="Canonical Owner",
                    role="viewer",
                    password_hash=hash_password("build-231-test-password"),
                    is_active=True,
                ),
            ]
        )
        db.commit()

        with pytest.raises(EmailDomainMigrationConflict):
            migrate_email_domain(db, apply=True)
        db.rollback()

        emails = set(db.scalars(select(UserAccount.email)))
        assert _email("owner", LEGACY_EMAIL_DOMAIN) in emails
        assert _email("OWNER", CANONICAL_EMAIL_DOMAIN) in emails


def test_bootstrap_admin_rejects_retired_domain() -> None:
    with pytest.raises(RuntimeError, match="retired company email domain"):
        validate_bootstrap_admin_email(_email("admin", LEGACY_EMAIL_DOMAIN))
    assert validate_bootstrap_admin_email(_email("ADMIN", CANONICAL_EMAIL_DOMAIN)) == _email(
        "admin", CANONICAL_EMAIL_DOMAIN
    )
