from __future__ import annotations

from datetime import datetime

from app.schemas.rfq_draft import RFQDraftRequest, RFQDraftResponse


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "Not specified"
    return value.strftime("%Y-%m-%d %H:%M")


def _format_bullets(items: list[str]) -> str:
    if not items:
        return "- Please quote the applicable scope shown in the attached drawings and specifications."
    return "\n".join(f"- {item}" for item in items)


def _format_attachments(attachment_names: list[str]) -> str:
    if not attachment_names:
        return "Relevant drawings/specifications will be provided as applicable."
    return "\n".join(f"- {name}" for name in attachment_names)


def _format_signature(payload: RFQDraftRequest) -> str:
    lines = ["Thank you,", "", payload.sender_name]
    if payload.sender_phone:
        lines.append(payload.sender_phone)
    if payload.sender_email:
        lines.append(str(payload.sender_email))
    return "\n".join(lines)


def build_rfq_draft(payload: RFQDraftRequest) -> RFQDraftResponse:
    subject = f"RFQ - {payload.project_name} - {payload.category} - {payload.supplier_name}"
    body = f"""Hello,

Iron House is pricing the following project and would appreciate your quotation for the applicable scope.

Project: {payload.project_name}
Location: {payload.project_location or "Not specified"}
Owner / Municipality: {payload.owner or "Not specified"}
Tender Close: {_format_datetime(payload.tender_close)}
Requested Quote Return: {_format_datetime(payload.quote_return_deadline)}

Requested scope:
{_format_bullets(payload.scope_items)}

Attachments / reference documents:
{_format_attachments(payload.attachment_names)}

Please include applicable supply, delivery, taxes, lead times, exclusions, quote validity, and any assumptions required for your pricing.

If this RFQ has reached the wrong inbox, please forward it to the correct estimator or provide the best estimating contact for future requests.

{_format_signature(payload)}
"""
    return RFQDraftResponse(
        subject=subject,
        body=body,
        recipient_email=payload.recipient_email,
        attachment_names=payload.attachment_names,
    )
