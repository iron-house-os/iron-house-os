from dataclasses import dataclass
import re
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import Employee
from app.services.auth import AuthenticatedUser


HelpAudience = Literal["employee", "foreman", "management"]


@dataclass(frozen=True)
class HelpArticle:
    id: str
    title: str
    path: str
    audiences: frozenset[HelpAudience]
    keywords: tuple[str, ...]
    summary: str
    steps: tuple[str, ...]
    expected_result: str
    approval_note: str | None = None


EMPLOYEE_AND_FOREMAN = frozenset({"employee", "foreman"})
ALL_AUDIENCES = frozenset({"employee", "foreman", "management"})

APPROVED_HELP_ARTICLES: tuple[HelpArticle, ...] = (
    HelpArticle(
        id="employee-enter-time",
        title="Enter my time",
        path="/employee-portal/time",
        audiences=frozenset({"employee"}),
        keywords=("time", "hours", "timesheet", "shift", "job"),
        summary="Add your hours to the correct day and job, then review them before saving.",
        steps=(
            "Open Time in the Employee Portal.",
            "Choose the work date and the correct project.",
            "Enter your hours and the work details requested on the page.",
            "Review the date, project and total hours.",
            "Save or submit the entry.",
        ),
        expected_result="Your time entry is saved for supervisor or management review.",
        approval_note="A saved entry is not the same as payroll approval.",
    ),
    HelpArticle(
        id="employee-submit-receipt",
        title="Submit a receipt",
        path="/employee-portal/receipts",
        audiences=EMPLOYEE_AND_FOREMAN,
        keywords=("receipt", "expense", "reimbursement", "company card", "photo"),
        summary="Upload a clear photo, check the extracted details and submit it for review.",
        steps=(
            "Open Receipts in your portal.",
            "Take or select a clear photo of every receipt page.",
            "Check the vendor, date, payment method, taxes and total.",
            "Add the project or coding details you know.",
            "Submit the receipt for review.",
        ),
        expected_result=(
            "The receipt is queued for Financial Control review; it is not posted automatically."
        ),
        approval_note=(
            "Financial Control reviews coding, totals and duplicates before approval or export."
        ),
    ),
    HelpArticle(
        id="employee-check-schedule",
        title="Check my schedule",
        path="/employee-portal/schedule",
        audiences=EMPLOYEE_AND_FOREMAN,
        keywords=("schedule", "shift", "crew", "tomorrow", "where", "when"),
        summary="Open the schedule assigned to your portal and review the job details.",
        steps=(
            "Open Schedule in your portal.",
            "Find the correct date.",
            "Review the project, start information and notes.",
            "Contact your supervisor if anything is missing or incorrect.",
        ),
        expected_result="You know the current assignment shown in Iron House OS.",
        approval_note=(
            "If field instructions conflict with the schedule, confirm with your supervisor."
        ),
    ),
    HelpArticle(
        id="field-complete-flha",
        title="Complete the daily FLHA",
        path="/employee-portal/safety",
        audiences=ALL_AUDIENCES,
        keywords=("flha", "safety", "hazard", "control", "assessment", "field level"),
        summary=(
            "Verify actual site conditions, review every control and post the FLHA to the job folder."
        ),
        steps=(
            "Open Safety and select the correct project or job.",
            "Complete the rapid hazard screening for actual site conditions.",
            "Add each task, hazard, control and responsible person.",
            "Resolve every critical-hazard blocker and review the emergency details.",
            "Review the FLHA, then post it for crew acknowledgement and supervisor release.",
        ),
        expected_result=(
            "A versioned FLHA is saved in the job folder for acknowledgement and release."
        ),
        approval_note=(
            "Help or AI suggestions never declare work safe. Stop work and contact the supervisor "
            "whenever conditions are unsafe or unclear."
        ),
    ),
    HelpArticle(
        id="field-request-po",
        title="Request a purchase order",
        path="/request-po",
        audiences=ALL_AUDIENCES,
        keywords=("po", "purchase order", "buy", "supplier", "approval", "material"),
        summary=(
            "Send the purchase details to the designated approver and wait for the approved PO number."
        ),
        steps=(
            "Open Request PO.",
            "Select the correct project and supplier when known.",
            "Describe what is needed, the reason and the expected amount.",
            "Review the request and submit it.",
            "Wait for the approver's decision and PO number before purchasing.",
        ),
        expected_result="A traceable PO request is sent for approval.",
        approval_note="Submitting a request does not authorize a purchase.",
    ),
    HelpArticle(
        id="field-inspect-equipment",
        title="Inspect small equipment",
        path="/employee-portal/small-equipment",
        audiences=ALL_AUDIENCES,
        keywords=("equipment", "inspection", "tool", "repair", "damage", "unsafe"),
        summary=(
            "Check the item, record its condition and flag anything unsafe or needing repair."
        ),
        steps=(
            "Open Small Equipment and choose the employee and project.",
            "Identify the equipment type and asset.",
            "Check guards, controls, cords or hoses, leaks and damage.",
            "Choose the condition and add clear comments or photos.",
            "Review and submit the inspection.",
        ),
        expected_result=(
            "The condition is recorded and flagged items are visible to management."
        ),
        approval_note="Remove unsafe equipment from service and notify the supervisor immediately.",
    ),
    HelpArticle(
        id="foreman-crew-time",
        title="Enter crew time",
        path="/foreman-portal/time",
        audiences=frozenset({"foreman"}),
        keywords=("crew time", "foreman", "daily timesheet", "hours", "labour"),
        summary="Record crew hours against the correct project and review the daily sheet.",
        steps=(
            "Open Time in the Foreman Portal.",
            "Choose the work date and project.",
            "Add each crew member and their hours.",
            "Check the crew total and work details.",
            "Save or submit the daily sheet for review.",
        ),
        expected_result="The daily crew timesheet is saved for management review.",
        approval_note="Review does not replace payroll approval.",
    ),
    HelpArticle(
        id="foreman-record-production",
        title="Record daily production",
        path="/foreman-portal/production",
        audiences=frozenset({"foreman"}),
        keywords=("production", "quantity", "loads", "progress", "foreman", "daily"),
        summary=(
            "Save the day's production against the correct job with supporting notes or photos."
        ),
        steps=(
            "Open Production or Loads in the Foreman Portal.",
            "Select the correct date and project.",
            "Enter the activity, quantity, unit and supporting details.",
            "Attach clear evidence when it is available.",
            "Review and save the record.",
        ),
        expected_result="A traceable daily production record is attached to the job.",
    ),
    HelpArticle(
        id="management-verbal-quote",
        title="Start a verbal quote",
        path="/customer-quotes",
        audiences=frozenset({"management"}),
        keywords=("verbal quote", "customer", "scope", "price", "acceptance", "award"),
        summary="Capture the customer, scope and assumptions before preparing or issuing a quote.",
        steps=(
            "Open Customer Quotes and start a new verbal quote.",
            "Record the customer, contact, site and scope requested.",
            "Add pricing, assumptions, exclusions and validity details.",
            "Review the draft before it is issued.",
            "Record customer acceptance only when evidence is available.",
        ),
        expected_result=(
            "A controlled quote record is ready for review, issue and eventual award handoff."
        ),
        approval_note="Quote acceptance and project award remain explicit management actions.",
    ),
    HelpArticle(
        id="management-create-project",
        title="Create or open a project",
        path="/projects",
        audiences=frozenset({"management"}),
        keywords=("project", "job", "workspace", "awarded", "setup", "job number"),
        summary=(
            "Create the project once, then use its workspace to reach documents, RFQs, estimating "
            "and readiness."
        ),
        steps=(
            "Open Projects and search before creating a new record.",
            "Open the existing project, or choose the correct stage for a new one.",
            "Enter the required customer, name and project details.",
            "Save the project and keep it selected as the active project.",
            "Use the project workspace for the next task.",
        ),
        expected_result=(
            "One central project record is available to the connected OS functions."
        ),
        approval_note="Do not create a duplicate project when a matching job already exists.",
    ),
    HelpArticle(
        id="management-build-estimate",
        title="Build an estimate",
        path="/estimating",
        audiences=frozenset({"management"}),
        keywords=("estimate", "cost", "markup", "production rate", "risk", "workbook"),
        summary=(
            "Build the estimate within the active project and review its assumptions before export."
        ),
        steps=(
            "Open Estimating with the correct active project.",
            "Add the work items, quantities, production rates and costs.",
            "Add markups, risk and estimate notes.",
            "Review the summary and unresolved assumptions.",
            "Save the workspace or export the workbook for review.",
        ),
        expected_result="A saved, project-linked estimate is ready for internal review.",
        approval_note="Exporting an estimate does not approve a bid or customer price.",
    ),
    HelpArticle(
        id="management-upload-document",
        title="Add a project document",
        path="/document-operations",
        audiences=frozenset({"management"}),
        keywords=("document", "upload", "drawing", "specification", "addendum", "revision"),
        summary="Upload the source file once, label it clearly and keep its revision traceable.",
        steps=(
            "Open Document Operations with the correct active project.",
            "Choose the file and the correct document type.",
            "Enter a clear title, date and revision information.",
            "Review the project and metadata.",
            "Upload the document and confirm it appears in the project record.",
        ),
        expected_result=(
            "A traceable project document is available to connected workflows."
        ),
        approval_note=(
            "Preserve source documents; do not replace an old revision without recording the new one."
        ),
    ),
    HelpArticle(
        id="management-build-rfq",
        title="Build an RFQ package",
        path="/rfq-builder",
        audiences=frozenset({"management"}),
        keywords=("rfq", "supplier", "quote", "package", "attachments", "bid"),
        summary=(
            "Select suppliers and controlled project documents, then review package readiness."
        ),
        steps=(
            "Open RFQ Builder with the correct active project.",
            "Define the requested scope and response date.",
            "Select the intended suppliers.",
            "Add only the correct controlled documents and revisions.",
            "Resolve readiness warnings before issuing anything.",
        ),
        expected_result=(
            "A project-linked RFQ package is ready for controlled review or issue."
        ),
        approval_note="Readiness does not authorize sending or committing the company.",
    ),
    HelpArticle(
        id="operations-onboard-employee",
        title="Onboard a new employee",
        path="/employee-onboarding",
        audiences=frozenset({"management"}),
        keywords=("employee", "onboarding", "new hire", "invitation", "orientation", "activate"),
        summary=(
            "Use the controlled invitation and review process; restricted information stays restricted."
        ),
        steps=(
            "Open Employee Onboarding and create the new-hire record.",
            "Generate and deliver the secure invitation.",
            "Review the returned package and request corrections if needed.",
            "Approve the package and complete required orientation evidence.",
            "Activate access only after deployment readiness passes.",
        ),
        expected_result=(
            "The employee has a reviewed onboarding record and appropriately controlled OS access."
        ),
        approval_note=(
            "Activation is a management-controlled action; invitation completion alone is not approval."
        ),
    ),
)

STOP_WORDS = {
    "a",
    "about",
    "and",
    "can",
    "do",
    "for",
    "how",
    "i",
    "in",
    "is",
    "it",
    "my",
    "of",
    "on",
    "the",
    "to",
    "what",
    "where",
}
RESTRICTED_TERMS = (
    "password",
    "api key",
    "secret key",
    "social insurance",
    "bank account",
    "banking",
    "medical",
    "payroll",
    "disciplinary",
    "first aid",
)


def resolve_help_audience(db: Session, user: AuthenticatedUser) -> HelpAudience:
    if user.role != "viewer":
        return "management"
    employee = db.scalar(
        select(Employee).where(func.lower(Employee.email) == user.email.strip().lower())
    )
    if employee is not None and employee.portal_role == "foreman":
        return "foreman"
    return "employee"


def _terms(value: str) -> set[str]:
    return {
        item
        for item in re.findall(r"[a-z0-9]+", value.lower())
        if len(item) > 1 and item not in STOP_WORDS
    }


def _path_matches(route: str, path: str) -> bool:
    return route == path or route.startswith(f"{path}/")


def select_help_articles(
    message: str,
    audience: HelpAudience,
    route: str = "",
    *,
    limit: int = 3,
) -> list[HelpArticle]:
    normalized_message = f" {message.strip().lower()} "
    query_terms = _terms(message)
    ranked: list[tuple[int, str, HelpArticle]] = []
    for article in APPROVED_HELP_ARTICLES:
        if audience not in article.audiences:
            continue
        keyword_terms = _terms(" ".join(article.keywords))
        body_terms = _terms(
            " ".join(
                (
                    article.title,
                    article.summary,
                    article.expected_result,
                    *article.steps,
                )
            )
        )
        score = 3 * len(query_terms & keyword_terms) + len(query_terms & body_terms)
        score += sum(4 for keyword in article.keywords if f" {keyword.lower()} " in normalized_message)
        if route and _path_matches(route, article.path):
            score += 8
        if score > 0:
            ranked.append((score, article.id, article))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in ranked[: max(1, limit)]]


def is_restricted_help_message(message: str) -> bool:
    normalized = f" {message.strip().lower()} "
    return "sin" in _terms(message) or any(term in normalized for term in RESTRICTED_TERMS)


def format_help_context(articles: list[HelpArticle]) -> str:
    sections: list[str] = []
    for article in articles:
        details = [
            f"ARTICLE ID: {article.id}",
            f"TITLE: {article.title}",
            f"IHOS PATH: {article.path}",
            f"SUMMARY: {article.summary}",
            "STEPS:",
            *(f"{index}. {step}" for index, step in enumerate(article.steps, start=1)),
            f"EXPECTED RESULT: {article.expected_result}",
        ]
        if article.approval_note:
            details.append(f"APPROVAL OR SAFETY NOTE: {article.approval_note}")
        sections.append("\n".join(details))
    return "\n\n---\n\n".join(sections)


def static_help_answer(article: HelpArticle) -> str:
    lines = [article.summary, "", *(f"{index}. {step}" for index, step in enumerate(article.steps, 1))]
    lines.extend(("", f"What happens next: {article.expected_result}"))
    if article.approval_note:
        lines.extend(("", f"Important: {article.approval_note}"))
    return "\n".join(lines)
