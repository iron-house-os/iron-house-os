from textwrap import wrap

from app.schemas.customer_quote import CustomerQuoteRead
from app.services.flha_pdf import _build_pdf


def render_customer_quote_pdf(quote: CustomerQuoteRead) -> bytes:
    lines = [
        "IRON HOUSE CONTRACTING LTD.",
        "CUSTOMER QUOTE",
        "Corporation no. 1189400-5 | GST/HST no. 747415339RT0001",
        f"Quote: {quote.quote_number} | Status: {quote.status.value.upper()}",
        f"Quote date: {quote.quote_date} | Valid until: {quote.valid_until or 'Not specified'}",
        "",
        f"Prepared for: {quote.customer_name}",
        f"Email: {quote.customer_email or 'Not provided'} | Phone: {quote.customer_phone or 'Not provided'}",
        f"Project: {quote.project_name}",
        f"Site: {quote.site_address or 'Not provided'}",
        "",
        "SCOPE",
    ]
    lines.extend(wrap(quote.scope_summary, 96, break_long_words=False))
    lines.extend(["", "PRICING"])
    for item in quote.line_items:
        lines.extend(
            wrap(
                f"{item['description']}: {item['quantity']} {item['unit']} x ${item['unit_price']} = ${item['amount']}",
                96,
                break_long_words=False,
            )
        )
    if quote.assumptions:
        lines.extend(["", "ASSUMPTIONS", *[f"- {value}" for value in quote.assumptions]])
    if quote.exclusions:
        lines.extend(["", "EXCLUSIONS", *[f"- {value}" for value in quote.exclusions]])
    lines.extend(
        [
            "",
            f"Subtotal: ${quote.subtotal}",
            f"GST ({quote.gst_rate}%): ${quote.gst}",
            f"TOTAL CAD: ${quote.total}",
            "",
            quote.notes or "",
            "A draft or sent quote is not an award. Work proceeds only after documented acceptance.",
        ]
    )
    return _build_pdf([lines])
