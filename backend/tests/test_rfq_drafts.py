from datetime import datetime

from app.schemas.rfq_draft import RFQDraftRequest
from app.services.rfq_drafts import build_rfq_draft


def test_build_rfq_draft_generates_subject_and_body() -> None:
    payload = RFQDraftRequest(
        project_name="Marine Drive Parking Lot",
        project_location="White Rock, BC",
        owner="City of White Rock",
        tender_close=datetime(2026, 7, 15, 14, 0),
        quote_return_deadline=datetime(2026, 7, 14, 12, 0),
        category="Asphalt",
        supplier_name="Superior Paving",
        recipient_email="estimating@example.com",
        scope_items=["Supply and place asphalt", "Include tie-ins and sawcut edges"],
        attachment_names=["Civil Drawings.pdf", "Addendum 1.pdf"],
        sender_name="Iron House Estimating",
        sender_phone="604-000-0000",
        sender_email="estimating@ironhouse.example",
    )

    draft = build_rfq_draft(payload)

    assert draft.subject == "RFQ - Marine Drive Parking Lot - Asphalt - Superior Paving"
    assert draft.recipient_email == "estimating@example.com"
    assert "Project: Marine Drive Parking Lot" in draft.body
    assert "Location: White Rock, BC" in draft.body
    assert "Tender Close: 2026-07-15 14:00" in draft.body
    assert "Requested Quote Return: 2026-07-14 12:00" in draft.body
    assert "- Supply and place asphalt" in draft.body
    assert "- Include tie-ins and sawcut edges" in draft.body
    assert "- Civil Drawings.pdf" in draft.body
    assert "- Addendum 1.pdf" in draft.body
    assert "wrong inbox" in draft.body
    assert "Iron House Estimating" in draft.body


def test_build_rfq_draft_uses_default_scope_when_scope_items_missing() -> None:
    payload = RFQDraftRequest(
        project_name="Test Project",
        category="Pipe / Utilities",
        supplier_name="EMCO",
    )

    draft = build_rfq_draft(payload)

    assert "Please quote the applicable scope" in draft.body
    assert "Relevant drawings/specifications will be provided" in draft.body
