from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import re
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.contact import Contact
from app.models.field_operations import FieldRecord
from app.models.rfq import RFQPackage
from app.models.supplier import Supplier
from app.models.user import Employee, LoginThrottle, UserAccount
from app.services.auth import login_subject_hash

LEGACY_EMAIL_DOMAIN = "ironhousecivil.com"
CANONICAL_EMAIL_DOMAIN = "ironhousecontracting.com"


@dataclass(frozen=True)
class EmailDomainChange:
    area: str
    record_id: str
    field: str
    previous: str
    replacement: str


@dataclass(frozen=True)
class EmailDomainMigrationReport:
    applied: bool
    from_domain: str
    to_domain: str
    changes: tuple[EmailDomainChange, ...]
    sessions_invalidated: int
    login_throttles_cleared: int
    protected_history_policy: str = "Historical audit and provenance fields were not changed."

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["change_count"] = len(self.changes)
        counts: dict[str, int] = {}
        for change in self.changes:
            counts[change.area] = counts.get(change.area, 0) + 1
        payload["changes_by_area"] = counts
        return payload


class EmailDomainMigrationConflict(ValueError):
    def __init__(self, conflicts: list[str]) -> None:
        self.conflicts = tuple(conflicts)
        super().__init__("Email-domain migration blocked: " + "; ".join(conflicts))


def _normalise_domain(value: str) -> str:
    return value.strip().lower().lstrip("@")


def _replacement(value: str | None, from_domain: str, to_domain: str) -> str | None:
    if value is None or "@" not in value:
        return value
    local_part, domain = value.strip().rsplit("@", 1)
    if not local_part or domain.casefold() != from_domain.casefold():
        return value
    return f"{local_part}@{to_domain}".lower()


def _text_replacement(value: str, from_domain: str, to_domain: str) -> str:
    pattern = re.compile(
        rf"(?P<local>[A-Z0-9.!#$%&'*+/=?^_`{{|}}~-]+)@{re.escape(from_domain)}\b",
        re.IGNORECASE,
    )
    return pattern.sub(
        lambda match: f"{match.group('local').lower()}@{to_domain}",
        value,
    )


def _change(
    changes: list[EmailDomainChange],
    *,
    area: str,
    record_id: object,
    field: str,
    previous: str | None,
    replacement: str | None,
) -> bool:
    if previous is None or replacement is None or previous == replacement:
        return False
    changes.append(
        EmailDomainChange(
            area=area,
            record_id=str(record_id),
            field=field,
            previous=previous,
            replacement=replacement,
        )
    )
    return True


def _collision_conflicts(
    rows: list[UserAccount] | list[Employee],
    *,
    area: str,
    from_domain: str,
    to_domain: str,
) -> list[str]:
    projected: dict[str, list[str]] = {}
    conflicts: list[str] = []
    for row in rows:
        replacement = _replacement(row.email, from_domain, to_domain)
        assert replacement is not None
        if len(replacement) > 255:
            conflicts.append(f"{area} record {row.id} would exceed the 255-character email limit")
        projected.setdefault(replacement.casefold(), []).append(str(row.id))
    for email, record_ids in projected.items():
        if len(record_ids) > 1:
            conflicts.append(f"{area} records {', '.join(record_ids)} would collide at {email}")
    return conflicts


def _migrate_supplier_metadata(
    supplier: Supplier,
    from_domain: str,
    to_domain: str,
    changes: list[EmailDomainChange],
) -> dict[str, Any] | None:
    metadata = deepcopy(supplier.metadata_json or {})
    previous = metadata.get("email")
    if not isinstance(previous, str):
        return None
    replacement = _replacement(previous, from_domain, to_domain)
    if _change(
        changes,
        area="supplier_routing",
        record_id=supplier.id,
        field="metadata.email",
        previous=previous,
        replacement=replacement,
    ):
        metadata["email"] = replacement
        return metadata
    return None


def _migrate_rfq_metadata(
    rfq_package: RFQPackage,
    from_domain: str,
    to_domain: str,
    changes: list[EmailDomainChange],
) -> dict[str, Any] | None:
    metadata = deepcopy(rfq_package.metadata_json or {})
    changed = False

    supplier_contacts = metadata.get("supplier_contacts")
    if isinstance(supplier_contacts, dict):
        for supplier_id, contact in supplier_contacts.items():
            if not isinstance(contact, dict) or not isinstance(contact.get("recipient_email"), str):
                continue
            previous = contact["recipient_email"]
            replacement = _replacement(previous, from_domain, to_domain)
            if _change(
                changes,
                area="rfq_routing",
                record_id=rfq_package.id,
                field=f"supplier_contacts.{supplier_id}.recipient_email",
                previous=previous,
                replacement=replacement,
            ):
                contact["recipient_email"] = replacement
                changed = True

    workflow = metadata.get("gmail_drive_workflow")
    if isinstance(workflow, dict):
        sender = workflow.get("sender")
        if isinstance(sender, dict) and isinstance(sender.get("email"), str):
            previous = sender["email"]
            replacement = _replacement(previous, from_domain, to_domain)
            if _change(
                changes,
                area="rfq_routing",
                record_id=rfq_package.id,
                field="gmail_drive_workflow.sender.email",
                previous=previous,
                replacement=replacement,
            ):
                sender["email"] = replacement
                changed = True
        drafts = workflow.get("gmail_drafts")
        if isinstance(drafts, list):
            for index, draft in enumerate(drafts):
                if not isinstance(draft, dict):
                    continue
                for field in ("to", "body"):
                    previous = draft.get(field)
                    if not isinstance(previous, str):
                        continue
                    replacement = (
                        _replacement(previous, from_domain, to_domain)
                        if field == "to"
                        else _text_replacement(previous, from_domain, to_domain)
                    )
                    if _change(
                        changes,
                        area="rfq_routing",
                        record_id=rfq_package.id,
                        field=f"gmail_drive_workflow.gmail_drafts.{index}.{field}",
                        previous=previous,
                        replacement=replacement,
                    ):
                        draft[field] = replacement
                        changed = True
    return metadata if changed else None


def _migrate_alert_recipients(
    field_record: FieldRecord,
    from_domain: str,
    to_domain: str,
    changes: list[EmailDomainChange],
) -> list[Any] | None:
    recipients = list(field_record.alert_recipients or [])
    changed = False
    for index, recipient in enumerate(recipients):
        if not isinstance(recipient, str):
            continue
        replacement = _replacement(recipient, from_domain, to_domain)
        if _change(
            changes,
            area="field_routing",
            record_id=field_record.id,
            field=f"alert_recipients.{index}",
            previous=recipient,
            replacement=replacement,
        ):
            recipients[index] = replacement
            changed = True
    return recipients if changed else None


def migrate_email_domain(
    db: Session,
    *,
    from_domain: str = LEGACY_EMAIL_DOMAIN,
    to_domain: str = CANONICAL_EMAIL_DOMAIN,
    apply: bool = False,
) -> EmailDomainMigrationReport:
    source = _normalise_domain(from_domain)
    target = _normalise_domain(to_domain)
    if not source or not target or source == target:
        raise ValueError("Source and target email domains must be different non-empty domains.")

    accounts = list(db.scalars(select(UserAccount).with_for_update()))
    employees = list(db.scalars(select(Employee).with_for_update()))
    contacts = list(db.scalars(select(Contact).with_for_update()))
    suppliers = list(db.scalars(select(Supplier).with_for_update()))
    rfq_packages = list(db.scalars(select(RFQPackage).with_for_update()))
    field_records = list(db.scalars(select(FieldRecord).with_for_update()))

    conflicts = _collision_conflicts(
        accounts,
        area="user_accounts",
        from_domain=source,
        to_domain=target,
    )
    conflicts.extend(
        _collision_conflicts(
            employees,
            area="employees",
            from_domain=source,
            to_domain=target,
        )
    )
    if conflicts:
        raise EmailDomainMigrationConflict(conflicts)

    changes: list[EmailDomainChange] = []
    changed_accounts: list[tuple[UserAccount, str, str]] = []
    changed_employees: list[tuple[Employee, str]] = []
    changed_contacts: list[tuple[Contact, str]] = []
    changed_suppliers: list[tuple[Supplier, dict[str, Any]]] = []
    changed_packages: list[tuple[RFQPackage, dict[str, Any]]] = []
    changed_records: list[tuple[FieldRecord, list[Any]]] = []

    for account in accounts:
        replacement = _replacement(account.email, source, target)
        if _change(
            changes,
            area="user_accounts",
            record_id=account.id,
            field="email",
            previous=account.email,
            replacement=replacement,
        ):
            assert replacement is not None
            changed_accounts.append((account, account.email, replacement))
    for employee in employees:
        replacement = _replacement(employee.email, source, target)
        if _change(
            changes,
            area="employees",
            record_id=employee.id,
            field="email",
            previous=employee.email,
            replacement=replacement,
        ):
            assert replacement is not None
            changed_employees.append((employee, replacement))
    for contact in contacts:
        replacement = _replacement(contact.email, source, target)
        if _change(
            changes,
            area="contacts",
            record_id=contact.id,
            field="email",
            previous=contact.email,
            replacement=replacement,
        ):
            assert replacement is not None
            changed_contacts.append((contact, replacement))
    for supplier in suppliers:
        metadata = _migrate_supplier_metadata(supplier, source, target, changes)
        if metadata is not None:
            changed_suppliers.append((supplier, metadata))
    for rfq_package in rfq_packages:
        metadata = _migrate_rfq_metadata(rfq_package, source, target, changes)
        if metadata is not None:
            changed_packages.append((rfq_package, metadata))
    for field_record in field_records:
        recipients = _migrate_alert_recipients(field_record, source, target, changes)
        if recipients is not None:
            changed_records.append((field_record, recipients))

    cleared_throttles = 0
    if apply:
        for account, _, replacement in changed_accounts:
            account.email = replacement
            account.session_version += 1
        for employee, replacement in changed_employees:
            employee.email = replacement
        for contact, replacement in changed_contacts:
            contact.email = replacement
        for supplier, metadata in changed_suppliers:
            supplier.metadata_json = metadata
        for rfq_package, metadata in changed_packages:
            rfq_package.metadata_json = metadata
        for field_record, recipients in changed_records:
            field_record.alert_recipients = recipients

        throttle_hashes = {
            login_subject_hash(email)
            for _, previous, replacement in changed_accounts
            for email in (previous, replacement)
        }
        if throttle_hashes:
            result = db.execute(delete(LoginThrottle).where(LoginThrottle.key_hash.in_(throttle_hashes)))
            cleared_throttles = int(result.rowcount or 0)
        db.flush()

    return EmailDomainMigrationReport(
        applied=apply,
        from_domain=source,
        to_domain=target,
        changes=tuple(changes),
        sessions_invalidated=len(changed_accounts) if apply else 0,
        login_throttles_cleared=cleared_throttles,
    )
