import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from PIL import Image, ImageEnhance, ImageOps
import pytesseract

from app.schemas.receipt import ReceiptCreate

_AMOUNT = re.compile(r"(?<!\d)(\d{1,6}[.,]\d{2})(?!\d)")
_DATE_PATTERNS = (
    re.compile(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b"),
    re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2})\b"),
)


def extract_local_receipt(image_bytes: list[bytes], media_asset_ids: list) -> ReceiptCreate:
    """Conservative local OCR fallback used when the external AI provider is unavailable.

    The fallback only fills fields that can be identified with simple, auditable receipt
    conventions. All values remain an unapproved draft and receive reduced confidence.
    """
    texts = [_ocr_image(data) for data in image_bytes]
    text = "\n".join(part for part in texts if part).strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    vendor_name = _vendor(lines)
    receipt_date = _date(text)
    subtotal = _labelled_amount(lines, ("subtotal", "sub total"))
    gst = _labelled_amount(lines, ("gst", "g.s.t")) or Decimal("0")
    pst = _labelled_amount(lines, ("pst", "p.s.t")) or Decimal("0")
    other_tax = _labelled_amount(lines, ("tax", "hst")) or Decimal("0")
    total = _labelled_amount(lines, ("grand total", "amount due", "balance due", "total"))

    if total is None:
        amounts = [_amount(match.group(1)) for match in _AMOUNT.finditer(text)]
        valid = [value for value in amounts if value is not None]
        total = max(valid) if valid else None

    confidence: dict[str, float] = {}
    if vendor_name:
        confidence["vendor_name"] = 0.72
    if receipt_date:
        confidence["receipt_date"] = 0.75
    if subtotal is not None:
        confidence["subtotal"] = 0.72
    if total is not None:
        confidence["total"] = 0.78

    # Avoid double-counting a generic TAX line when explicit GST/PST was found.
    if gst or pst:
        other_tax = Decimal("0")

    return ReceiptCreate(
        media_asset_ids=media_asset_ids,
        vendor_name=vendor_name,
        receipt_date=receipt_date,
        currency="CAD",
        subtotal=float(subtotal) if subtotal is not None else None,
        gst=float(gst),
        pst=float(pst),
        other_tax=float(other_tax),
        total=float(total) if total is not None else None,
        treatment="needs_review",
        confidence=confidence,
        flags=["local_ocr_fallback", "needs_review"],
        line_items=[],
    )


def _ocr_image(data: bytes) -> str:
    image = Image.open(io.BytesIO(data))
    image = ImageOps.exif_transpose(image).convert("L")
    image = ImageOps.autocontrast(image)
    image = ImageEnhance.Contrast(image).enhance(1.6)
    return pytesseract.image_to_string(image, config="--psm 6")


def _vendor(lines: list[str]) -> str | None:
    ignored = ("receipt", "invoice", "thank you", "welcome", "www.", "http", "tel", "phone")
    for line in lines[:8]:
        cleaned = re.sub(r"\s+", " ", line).strip(" -_:|")
        lowered = cleaned.lower()
        if len(cleaned) < 3 or any(term in lowered for term in ignored):
            continue
        if _AMOUNT.search(cleaned) or sum(character.isalpha() for character in cleaned) < 3:
            continue
        return cleaned[:255]
    return None


def _date(text: str):
    for index, pattern in enumerate(_DATE_PATTERNS):
        match = pattern.search(text)
        if not match:
            continue
        try:
            if index == 0:
                year, month, day = map(int, match.groups())
            else:
                first, second, year = map(int, match.groups())
                # Canadian receipts commonly use YYYY-MM-DD or MM/DD/YYYY.
                month, day = (first, second) if first <= 12 else (second, first)
            return datetime(year, month, day).date()
        except ValueError:
            continue
    return None


def _labelled_amount(lines: list[str], labels: tuple[str, ...]) -> Decimal | None:
    for line in reversed(lines):
        lowered = line.lower()
        if not any(label in lowered for label in labels):
            continue
        matches = list(_AMOUNT.finditer(line))
        if matches:
            return _amount(matches[-1].group(1))
    return None


def _amount(value: str) -> Decimal | None:
    try:
        return Decimal(value.replace(",", ".")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None
