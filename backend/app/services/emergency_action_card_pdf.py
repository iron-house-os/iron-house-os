from textwrap import wrap

from app.models.field_operations import FieldRecord
from app.services.flha_pdf import _build_pdf


def render_emergency_action_card_pdf(record: FieldRecord) -> bytes:
    """Render a durable offline copy without adding a second source of truth."""
    details = record.details or {}
    lines: list[str] = []

    def add(value: str = "") -> None:
        lines.extend(wrap(str(value), width=96, break_long_words=False) or [""])

    add("IRON HOUSE CIVIL CONSTRUCTORS - EMERGENCY ACTION CARD")
    add(f"{details.get('project') or record.title} | Status: {record.status.upper()}")
    add(f"Record date: {record.work_date} | Record ID: {record.id}")
    add()
    add(f"SITE ADDRESS / ACCESS: {details.get('address') or 'Not recorded'}")
    add(f"MUSTER POINT: {details.get('muster') or 'Not recorded'}")
    add(f"FIRST AID: {details.get('firstAid') or 'Not recorded'}")
    add(f"EMERGENCY LEAD: {details.get('emergencyLead') or 'Not recorded'}")
    add(f"RESCUE / EVACUATION: {details.get('rescue') or 'Not recorded'}")
    add()
    add("OFFLINE COPY")
    add("Use this copy when connectivity is unavailable. Confirm the current online record when connectivity returns and replace this copy when site conditions change.")
    return _build_pdf([lines])
