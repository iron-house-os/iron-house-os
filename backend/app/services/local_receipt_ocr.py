import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract

from app.schemas.receipt import ReceiptCreate

_AMOUNT = re.compile(r"(?<!\d)(\d{1,6}[.,]\d{2})(?!\d)")
_DATE_PATTERNS = (
    re.compile(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b"),
    re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2}|\d{2})\b"),
)
_TIME = re.compile(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b")
_REFERENCE = re.compile(
    r"\b(?:invoice|receipt|inv|trans(?:action)?|order)\s*(?:#|no\.?|number)?\s*[:#-]?\s*([A-Z0-9-]{3,24})\b",
    re.IGNORECASE,
)
_ADDRESS_HINT = re.compile(
    r"\b(?:street|st\.?|road|rd\.?|avenue|ave\.?|broadway|drive|dr\.?|way|highway|hwy\.?|boulevard|blvd\.?)\b",
    re.IGNORECASE,
)


def extract_local_receipt(image_bytes: list[bytes], media_asset_ids: list) -> ReceiptCreate:
    """Conservative local OCR fallback used when the external AI provider is unavailable."""
    texts = [_ocr_image(data) for data in image_bytes]
    text = "\n".join(part for part in texts if part).strip()
    lines = [_clean_line(line) for line in text.splitlines()]
    lines = [line for line in lines if line]

    vendor_name = _vendor(lines)
    vendor_address = _address(lines)
    reference = _reference(text)
    receipt_date = _date(text)
    receipt_time = _time(text)
    subtotal = _labelled_amount(lines, ("subtotal", "sub total", "sub-total"))
    gst = _labelled_amount(lines, ("gst", "g.s.t")) or Decimal("0")
    pst = _labelled_amount(lines, ("pst", "p.s.t")) or Decimal("0")
    other_tax = _labelled_amount(lines, ("tax", "hst")) or Decimal("0")
    total = _labelled_amount(lines, ("grand total", "amount due", "balance due", "total"))

    if total is None:
        amounts = [_amount(match.group(1)) for match in _AMOUNT.finditer(text)]
        valid = [value for value in amounts if value is not None]
        total = max(valid) if valid else None

    if gst or pst:
        other_tax = Decimal("0")

    taxes = gst + pst + other_tax
    if subtotal is None and total is not None and taxes > 0 and total >= taxes:
        subtotal = (total - taxes).quantize(Decimal("0.01"))

    confidence: dict[str, float] = {}
    for field, value, score in (
        ("vendor_name", vendor_name, 0.74),
        ("vendor_address", vendor_address, 0.67),
        ("reference", reference, 0.72),
        ("receipt_date", receipt_date, 0.78),
        ("receipt_time", receipt_time, 0.72),
        ("subtotal", subtotal, 0.70),
        ("total", total, 0.82),
    ):
        if value is not None:
            confidence[field] = score

    return ReceiptCreate(
        media_asset_ids=media_asset_ids,
        vendor_name=vendor_name,
        vendor_address=vendor_address,
        reference=reference,
        receipt_date=receipt_date,
        receipt_time=receipt_time,
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

    if max(image.size) < 2400:
        scale = min(3, max(2, 2400 // max(image.size)))
        image = image.resize((image.width * scale, image.height * scale), Image.Resampling.LANCZOS)

    image = ImageOps.autocontrast(image, cutoff=1)
    image = ImageEnhance.Contrast(image).enhance(2.1)
    image = image.filter(ImageFilter.SHARPEN)

    variants = [
        image,
        image.point(lambda pixel: 255 if pixel > 165 else 0),
    ]
    candidates: list[str] = []
    for variant in variants:
        for psm in (6, 4):
            text = pytesseract.image_to_string(variant, config=f"--oem 3 --psm {psm}").strip()
            if text:
                candidates.append(text)
    return max(candidates, key=_ocr_quality, default="")


def _ocr_quality(text: str) -> tuple[int, int, int]:
    labelled = sum(term in text.lower() for term in ("total", "gst", "subtotal", "invoice", "date"))
    alpha = sum(character.isalpha() for character in text)
    return labelled, alpha, len(text)


def _clean_line(line: str) -> str:
    line = re.sub(r"[|]{2,}", " ", line)
    line = re.sub(r"\s+", " ", line).strip(" ;,:_-|~")
    return line


def _vendor(lines: list[str]) -> str | None:
    ignored = (
        "receipt", "invoice", "thank you", "welcome", "www.", "http", "tel", "phone",
        "date", "time", "subtotal", "total", "gst", "pst", "cashier", "customer",
    )
    candidates: list[tuple[int, str]] = []
    for position, line in enumerate(lines[:12]):
        cleaned = _clean_vendor(line)
        lowered = cleaned.lower()
        letters = sum(character.isalpha() for character in cleaned)
        if len(cleaned) < 3 or letters < 3 or any(term in lowered for term in ignored):
            continue
        if _AMOUNT.search(cleaned) or _ADDRESS_HINT.search(cleaned):
            continue
        score = max(0, 12 - position)
        score += 4 if "&" in cleaned else 0
        score += 3 if cleaned.upper() == cleaned else 0
        score += min(letters // 4, 5)
        candidates.append((score, cleaned[:255]))
    return max(candidates, default=(0, None))[1]


def _clean_vendor(value: str) -> str:
    value = _clean_line(value)
    value = re.sub(r"^[^A-Za-z0-9]+", "", value)
    value = re.sub(r"\b(?:oe|oo|0e)\s*\d+$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value).strip(" ;,:_-|~")
    return value


def _address(lines: list[str]) -> str | None:
    for line in lines[:15]:
        if _ADDRESS_HINT.search(line) and any(character.isdigit() for character in line):
            return line[:500]
    return None


def _reference(text: str) -> str | None:
    match = _REFERENCE.search(text)
    return match.group(1).strip("-_") if match else None


def _time(text: str) -> str | None:
    match = _TIME.search(text)
    return f"{int(match.group(1)):02d}:{match.group(2)}" if match else None


def _date(text: str):
    for index, pattern in enumerate(_DATE_PATTERNS):
        match = pattern.search(text)
        if not match:
            continue
        try:
            if index == 0:
                year, month, day = map(int, match.groups())
            else:
                first, second, raw_year = match.groups()
                first, second, year = int(first), int(second), int(raw_year)
                year = year + 2000 if year < 100 else year
                month, day = (first, second) if first <= 12 else (second, first)
            return datetime(year, month, day).date()
        except ValueError:
            continue
    return None


def _labelled_amount(lines: list[str], labels: tuple[str, ...]) -> Decimal | None:
    for line in reversed(lines):
        lowered = line.lower()
        if not any(re.search(rf"\b{re.escape(label)}\b", lowered) for label in labels):
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
