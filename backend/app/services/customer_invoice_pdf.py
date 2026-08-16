from textwrap import wrap

from app.schemas.finance import CustomerInvoiceRead
from app.services.flha_pdf import _build_pdf


def render_customer_invoice_pdf(invoice: CustomerInvoiceRead) -> bytes:
    lines = [
        "IRON HOUSE CONTRACTING LTD.",
        "CUSTOMER INVOICE",
        "Corporation no. 1189400-5 | GST/HST no. 747415339RT0001",
        f"Invoice: {invoice.invoice_number} | Status: {invoice.status.upper()}",
        f"Invoice date: {invoice.invoice_date} | Due: {invoice.due_date} | {invoice.terms}",
        "",
        f"Bill to: {invoice.customer_name}", invoice.customer_address,
        f"Phone: {invoice.customer_phone or 'Not provided'}",
        f"Project: {invoice.project_name}",
        f"Site: {invoice.site_address or 'Not provided — do not substitute customer office'}",
        "",
    ]
    for item in invoice.line_items:
        lines.extend(wrap(f"{item['description']}: {item['quantity']} x ${item['unit_price']} = ${item['amount']}", 96, break_long_words=False))
    lines.extend(["", f"Subtotal: ${invoice.subtotal}", f"GST ({invoice.gst_rate}%): ${invoice.gst}", f"TOTAL CAD: ${invoice.total}", "", "Thank you for your business."])
    return _build_pdf([lines])
