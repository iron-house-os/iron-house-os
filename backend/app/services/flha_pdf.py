from textwrap import wrap

from app.models.field_operations import FieldRecord


def render_flha_pdf(record: FieldRecord) -> bytes:
    """Render a compact dependency-free PDF, keeping every signature block together."""
    details = record.details or {}
    lines: list[tuple[str, bool]] = []

    def add(value: str = "", *, signature: bool = False) -> None:
        chunks = wrap(str(value), width=96, break_long_words=False, replace_whitespace=True) or [""]
        lines.extend((chunk, signature) for chunk in chunks)

    add("IRON HOUSE CIVIL CONSTRUCTORS - FIELD LEVEL HAZARD ASSESSMENT")
    add(f"{record.title} | Version {details.get('version', 1)} | Status: {record.status.upper()}")
    add(f"Project: {details.get('project_name') or record.project_id or 'Not assigned'}")
    add(f"Site: {details.get('site_location', '')} | Date/time: {details.get('assessment_datetime', record.work_date)}")
    add(f"Supervisor: {(details.get('supervisor') or {}).get('name', '')} | First aid: {(details.get('first_aid_attendant') or {}).get('name', '')}")
    add(f"Weather: {details.get('weather', '')}")
    add()
    add("SCREENING - Yes / No / N/A")
    for key, answer in (details.get("screening") or {}).items():
        add(f"{key.replace('_', ' ').title()}: {str(answer).upper()}")
    add()
    add("TASK | HAZARD | CONTROL | RESPONSIBLE PERSON")
    for index, row in enumerate(details.get("hazards") or [], start=1):
        add(f"{index}. {row.get('task', '')} | {row.get('hazard', '')} | {row.get('control', '')} | {row.get('responsible_person', '')}")
        add(f"   Control level: {str(row.get('control_level', '')).title()} | Risk: {str(row.get('risk', '')).title()} | Accepted: {'Yes' if row.get('accepted_control') else 'No'} | Evidence: {row.get('evidence') or 'N/A'}")
    add()
    add("EMERGENCY AND STOP-WORK PLAN")
    for key, value in (details.get("emergency") or {}).items():
        add(f"{key.replace('_', ' ').title()}: {value}")
    add()
    add("CREW ACKNOWLEDGEMENTS")
    signatures = record.signatures or []
    for member in details.get("crew") or []:
        signature = next((item for item in signatures if item.get("employee_id") == str(member.get("id"))), None)
        if signature:
            add(f"Worker: {member.get('name', '')}", signature=True)
            add(f"Signed: {signature.get('signed_at', '')} | Method: {str(signature.get('signing_method', '')).replace('_', ' ')}", signature=True)
            add(f"Acknowledgement: {signature.get('acknowledgement', '')}", signature=True)
        else:
            add(f"Worker: {member.get('name', '')} | NOT YET ACKNOWLEDGED", signature=True)
            add("Signature: ____________________________________", signature=True)
            add("Date/time: ____________________________________", signature=True)
        add()
    release = details.get("supervisor_release") or {}
    if release:
        add()
        add(f"SUPERVISOR RELEASE - {release.get('display_name', '')} at {release.get('released_at', '')}")
        add(f"Verification: {release.get('verification', '')}")

    pages: list[list[str]] = [[]]
    index = 0
    while index < len(lines):
        text, is_signature = lines[index]
        if is_signature:
            group: list[str] = []
            while index < len(lines) and lines[index][1]:
                group.append(lines[index][0])
                index += 1
            if len(pages[-1]) + len(group) > 52:
                pages.append([])
            pages[-1].extend(group)
        else:
            if len(pages[-1]) >= 52:
                pages.append([])
            pages[-1].append(text)
            index += 1

    return _build_pdf(pages)


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("latin-1", "replace").decode("latin-1")


def _build_pdf(pages: list[list[str]]) -> bytes:
    objects: list[bytes] = [b"", b""]
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_numbers: list[int] = []
    for page_lines in pages:
        content = "BT /F1 9 Tf 48 756 Td 12 TL " + " ".join(f"({_pdf_escape(line)}) Tj T*" for line in page_lines) + " ET"
        content_bytes = content.encode("latin-1")
        content_number = len(objects) + 1
        objects.append(f"<< /Length {len(content_bytes)} >>\nstream\n".encode() + content_bytes + b"\nendstream")
        page_number = len(objects) + 1
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_number} 0 R >>".encode())
        page_numbers.append(page_number)
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{number} 0 R" for number in page_numbers)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_numbers)} >>".encode()
    result = bytearray(b"%PDF-1.4\n%IHOS\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(result))
        result.extend(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(result)
    result.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    result.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    result.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(result)
