from textwrap import wrap

from app.models.field_operations import FieldRecord
from app.services.flha_pdf import _build_pdf


def render_daily_timesheet_pdf(record: FieldRecord) -> bytes:
    """Render a compact daily sheet without blank overflow pages."""
    details = record.details or {}
    lines: list[str] = []

    def add(value: str = "") -> None:
        lines.extend(wrap(str(value), width=96, break_long_words=False) or [""])

    add("IRON HOUSE CIVIL CONSTRUCTORS - FOREMAN DAILY TIME SHEET")
    add(f"Job: {details.get('project_number') or ''} - {details.get('project_name') or ''}")
    add(f"Date: {record.work_date} | Shift: {str(details.get('shift', 'day')).title()} | Version: {details.get('version', 1)} | Status: {record.status.upper()}")
    add(f"Project manager: {details.get('project_manager_name') or 'Not assigned'} | Foreman: {details.get('supervisor_name') or ''}")
    add(f"Weather: {details.get('weather') or 'Not recorded'} | Site: {details.get('site_conditions') or 'Not recorded'}")
    add()
    add("CREW LABOUR")
    for worker in details.get("labour") or []:
        totals = (details.get("employee_totals") or {}).get(worker.get("employee_id"), {})
        add(f"{worker.get('employee_code')} | {worker.get('employee_name')} | {worker.get('classification')} | ST {totals.get('straight_time', 0):g} | OT {totals.get('overtime', 0):g}")
        for split in worker.get("splits") or []:
            add(f"  {split.get('cost_code')} - ST {split.get('straight_time', 0):g}, OT {split.get('overtime', 0):g}")
    if details.get("equipment"):
        add()
        add("EQUIPMENT")
        for equipment in details["equipment"]:
            add(f"{equipment.get('resource_name')} ({equipment.get('source')}) | {equipment.get('unit')} | {equipment.get('notes') or ''}")
            for split in equipment.get("splits") or []:
                add(f"  {split.get('cost_code')} - {split.get('quantity', 0):g}")
    if details.get("materials"):
        add()
        add("MATERIALS, FEES AND PRODUCTION")
        for item in details["materials"]:
            production = f" | Production {item.get('production_quantity')} {item.get('production_unit')}" if item.get("production_quantity") is not None else ""
            add(f"{item.get('description')} | {item.get('vendor_name')} | {item.get('cost_code')} | {item.get('quantity'):g} {item.get('unit')}{production}")
    narrative = details.get("narrative") or {}
    add()
    add("DAILY NARRATIVE")
    for key in ("work_completed", "delays_issues", "safety_quality_notes", "general_comments"):
        add(f"{key.replace('_', ' ').title()}: {narrative.get(key) or 'None recorded'}")
    if narrative.get("potential_change"):
        add(f"POTENTIAL CHANGE - REVIEW REQUIRED: {narrative.get('potential_change_details') or 'Flagged by foreman'}")
    totals = details.get("sheet_totals") or {}
    add()
    add(f"SHEET TOTAL - ST {totals.get('straight_time', 0):g} | OT {totals.get('overtime', 0):g} | LABOUR {totals.get('labour_hours', 0):g}")
    pages = [lines[index:index + 52] for index in range(0, len(lines), 52)] or [[""]]
    return _build_pdf(pages)
