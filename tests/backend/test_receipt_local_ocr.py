from uuid import UUID

from app.services import local_receipt_ocr


ASSET_ID = UUID("00000000-0000-0000-0000-000000000123")


def test_local_ocr_extracts_conservative_receipt_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        local_receipt_ocr,
        "_ocr_image",
        lambda _data: "HOME HARDWARE\n2026-08-03\nSUBTOTAL 100.00\nGST 5.00\nTOTAL 105.00",
    )

    draft = local_receipt_ocr.extract_local_receipt([b"image"], [ASSET_ID])

    assert draft.vendor_name == "HOME HARDWARE"
    assert str(draft.receipt_date) == "2026-08-03"
    assert draft.subtotal == 100
    assert draft.gst == 5
    assert draft.total == 105
    assert draft.line_items == []
    assert draft.treatment == "needs_review"
    assert "local_ocr_fallback" in draft.flags


def test_local_ocr_returns_reviewable_draft_when_only_total_is_visible(monkeypatch) -> None:
    monkeypatch.setattr(
        local_receipt_ocr,
        "_ocr_image",
        lambda _data: "THANK YOU\nAMOUNT DUE 42.19",
    )

    draft = local_receipt_ocr.extract_local_receipt([b"image"], [ASSET_ID])

    assert draft.vendor_name is None
    assert draft.total == 42.19
    assert draft.currency == "CAD"
    assert draft.confidence["total"] < 0.8
    assert "needs_review" in draft.flags
