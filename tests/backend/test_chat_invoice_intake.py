from collections.abc import Generator
from datetime import date
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from conftest import TestingSessionLocal
from app.models.project import Project
from app.schemas.chat_invoice_intake import (
    ChatInvoiceIntakeRecord,
    ChatInvoiceIntakeRequest,
)
from app.schemas.finance import CustomerInvoiceCreate
from app.services import chat_invoice_intake
from app.services.auth import AuthenticatedUser
from app.services.chat_invoice_intake import import_chat_invoices


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    with TestingSessionLocal() as session:
        yield session


def _user(role: str = "admin") -> AuthenticatedUser:
    return AuthenticatedUser(
        id=uuid4(),
        email=f"{role}@ironhousecivil.com",
        display_name=role,
        role=role,
        session_version=1,
    )


def _invoice(invoice_number: str = "CHAT-001", unit_price: str = "105.00") -> CustomerInvoiceCreate:
    return CustomerInvoiceCreate(
        invoice_number=invoice_number,
        project_name="Aria",
        site_address="13575 Commerce Parkway, Richmond, BC V6V 2L1",
        customer_name="Universal Construction",
        customer_address="PO Box 1120, Chilliwack, BC V2R 3N7",
        customer_phone="604-858-8618",
        invoice_date=date(2026, 8, 20),
        due_date=date(2026, 9, 19),
        line_items=[
            {
                "description": "Water testing and water service install",
                "quantity": "4.19",
                "unit_price": unit_price,
            }
        ],
    )


def _force_first_invoice_lookup_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    original_find_invoice = chat_invoice_intake._find_invoice
    lookup_count = 0

    def find_after_race(db_session, invoice_number):
        nonlocal lookup_count
        lookup_count += 1
        if lookup_count == 1:
            return None
        return original_find_invoice(db_session, invoice_number)

    monkeypatch.setattr(chat_invoice_intake, "_find_invoice", find_after_race)


def test_chat_invoice_intake_creates_project_and_draft_invoice(db_session) -> None:
    result = import_chat_invoices(
        db_session,
        ChatInvoiceIntakeRequest(items=[ChatInvoiceIntakeRecord(invoice=_invoice())]),
        _user(),
    )

    assert result.created_count == 1
    assert result.reused_count == 0
    item = result.items[0]
    assert item.status == "created"
    assert item.project_created is True
    assert item.project_id is not None
    assert item.invoice is not None
    assert item.invoice.project_id == item.project_id
    assert item.invoice.status == "draft"
    assert item.invoice.subtotal == "439.95"
    assert item.invoice.gst == "22.00"
    assert item.invoice.total == "461.95"


def test_chat_invoice_intake_is_idempotent_for_identical_retry(db_session) -> None:
    payload = ChatInvoiceIntakeRequest(items=[ChatInvoiceIntakeRecord(invoice=_invoice())])

    first = import_chat_invoices(db_session, payload, _user())
    project_count_after_first = db_session.scalar(select(func.count()).select_from(Project))
    second = import_chat_invoices(db_session, payload, _user())
    project_count_after_second = db_session.scalar(select(func.count()).select_from(Project))

    assert first.items[0].status == "created"
    assert second.items[0].status == "reused"
    assert second.reused_count == 1
    assert second.items[0].project_created is False
    assert second.items[0].project_id == first.items[0].project_id
    assert project_count_after_second == project_count_after_first


def test_chat_invoice_intake_reports_conflicting_invoice_without_project_side_effect(db_session) -> None:
    import_chat_invoices(
        db_session,
        ChatInvoiceIntakeRequest(items=[ChatInvoiceIntakeRecord(invoice=_invoice())]),
        _user(),
    )
    project_count_before_conflict = db_session.scalar(select(func.count()).select_from(Project))

    conflicting = _invoice(unit_price="106.00").model_copy(
        update={"project_name": "Different Project", "site_address": "999 Other Road"}
    )
    result = import_chat_invoices(
        db_session,
        ChatInvoiceIntakeRequest(items=[ChatInvoiceIntakeRecord(invoice=conflicting)]),
        _user(),
    )
    project_count_after_conflict = db_session.scalar(select(func.count()).select_from(Project))

    assert result.conflict_count == 1
    assert result.items[0].status == "conflict"
    assert result.items[0].project_created is False
    assert "different data" in (result.items[0].detail or "")
    assert project_count_after_conflict == project_count_before_conflict


def test_chat_invoice_intake_reuses_identical_concurrent_winner(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = ChatInvoiceIntakeRequest(items=[ChatInvoiceIntakeRecord(invoice=_invoice())])
    first = import_chat_invoices(db_session, payload, _user())
    project_count_before_race = db_session.scalar(select(func.count()).select_from(Project))
    _force_first_invoice_lookup_miss(monkeypatch)

    result = import_chat_invoices(db_session, payload, _user())
    project_count_after_race = db_session.scalar(select(func.count()).select_from(Project))

    assert result.reused_count == 1
    assert result.items[0].status == "reused"
    assert result.items[0].project_created is False
    assert result.items[0].project_id == first.items[0].project_id
    assert project_count_after_race == project_count_before_race


def test_chat_invoice_intake_rejects_conflicting_concurrent_winner_without_project_side_effect(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import_chat_invoices(
        db_session,
        ChatInvoiceIntakeRequest(items=[ChatInvoiceIntakeRecord(invoice=_invoice())]),
        _user(),
    )
    project_count_before_race = db_session.scalar(select(func.count()).select_from(Project))
    conflicting = _invoice(unit_price="106.00").model_copy(
        update={"project_name": "Concurrent Project", "site_address": "1000 Race Road"}
    )
    _force_first_invoice_lookup_miss(monkeypatch)

    result = import_chat_invoices(
        db_session,
        ChatInvoiceIntakeRequest(items=[ChatInvoiceIntakeRecord(invoice=conflicting)]),
        _user(),
    )
    project_count_after_race = db_session.scalar(select(func.count()).select_from(Project))

    assert result.conflict_count == 1
    assert result.items[0].status == "conflict"
    assert result.items[0].project_created is False
    assert project_count_after_race == project_count_before_race


def test_chat_invoice_intake_reuses_matching_project_for_new_invoice(db_session) -> None:
    first = import_chat_invoices(
        db_session,
        ChatInvoiceIntakeRequest(items=[ChatInvoiceIntakeRecord(invoice=_invoice())]),
        _user(),
    )
    second = import_chat_invoices(
        db_session,
        ChatInvoiceIntakeRequest(
            items=[ChatInvoiceIntakeRecord(invoice=_invoice(invoice_number="CHAT-002"))]
        ),
        _user(),
    )

    assert second.items[0].status == "created"
    assert second.items[0].project_created is False
    assert second.items[0].project_id == first.items[0].project_id


def test_chat_invoice_intake_strips_project_creation_fields(db_session) -> None:
    spaced = _invoice().model_copy(
        update={
            "project_name": "  Aria  ",
            "site_address": "  13575 Commerce Parkway, Richmond, BC V6V 2L1  ",
            "customer_name": "  Universal Construction  ",
        }
    )

    result = import_chat_invoices(
        db_session,
        ChatInvoiceIntakeRequest(items=[ChatInvoiceIntakeRecord(invoice=spaced)]),
        _user(),
    )
    project = db_session.get(Project, result.items[0].project_id)

    assert project is not None
    assert project.name == "Aria"
    assert project.project_address == "13575 Commerce Parkway, Richmond, BC V6V 2L1"
    assert project.client_owner == "Universal Construction"


def test_chat_invoice_intake_requires_management(db_session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        import_chat_invoices(
            db_session,
            ChatInvoiceIntakeRequest(items=[ChatInvoiceIntakeRecord(invoice=_invoice())]),
            _user("estimator"),
        )

    assert exc_info.value.status_code == 403
