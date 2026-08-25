from datetime import date
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.chat_invoice_intake import (
    ChatInvoiceIntakeRecord,
    ChatInvoiceIntakeRequest,
)
from app.schemas.finance import CustomerInvoiceCreate
from app.services.auth import AuthenticatedUser
from app.services.chat_invoice_intake import import_chat_invoices


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
    second = import_chat_invoices(db_session, payload, _user())

    assert first.items[0].status == "created"
    assert second.items[0].status == "reused"
    assert second.reused_count == 1
    assert second.items[0].project_created is False
    assert second.items[0].project_id == first.items[0].project_id


def test_chat_invoice_intake_reports_conflicting_invoice_number(db_session) -> None:
    import_chat_invoices(
        db_session,
        ChatInvoiceIntakeRequest(items=[ChatInvoiceIntakeRecord(invoice=_invoice())]),
        _user(),
    )

    result = import_chat_invoices(
        db_session,
        ChatInvoiceIntakeRequest(
            items=[ChatInvoiceIntakeRecord(invoice=_invoice(unit_price="106.00"))]
        ),
        _user(),
    )

    assert result.conflict_count == 1
    assert result.items[0].status == "conflict"
    assert "different data" in (result.items[0].detail or "")


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


def test_chat_invoice_intake_requires_management(db_session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        import_chat_invoices(
            db_session,
            ChatInvoiceIntakeRequest(items=[ChatInvoiceIntakeRecord(invoice=_invoice())]),
            _user("estimator"),
        )

    assert exc_info.value.status_code == 403
