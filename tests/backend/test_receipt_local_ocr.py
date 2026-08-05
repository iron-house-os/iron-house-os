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
    assert draft.confidence["total"] < 0.9
    assert "needs_review" in draft.flags


def test_local_ocr_cleans_noisy_vendor_and_extracts_header_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        local_receipt_ocr,
        "_ocr_image",
        lambda _data: (
            "; GOW & STEIN oe 3\n"
            "#3 - 1711 Broadway Street\n"
            "DATE 07/29/26 TIME 08:23 INVOICE # 153873\n"
            "GST 20.35\n"
            "TOTAL 523.17"
        ),
    )

    draft = local_receipt_ocr.extract_local_receipt([b"image"], [ASSET_ID])

    assert draft.vendor_name == "GOW & STEIN"
    assert draft.vendor_address == "#3 - 1711 Broadway Street"
    assert draft.reference == "153873"
    assert str(draft.receipt_date) == "2026-07-29"
    assert draft.receipt_time == "08:23"
    assert draft.gst == 20.35
    assert draft.subtotal == 502.82
    assert draft.total == 523.17


def test_generic_tax_does_not_match_total(monkeypatch) -> None:
    monkeypatch.setattr(
        local_receipt_ocr,
        "_ocr_image",
        lambda _data: "VENDOR SHOP\nTOTAL 100.00",
    )

    draft = local_receipt_ocr.extract_local_receipt([b"image"], [ASSET_ID])

    assert draft.other_tax == 0
    assert draft.total == 100
