from fastapi import APIRouter, Depends

from app.api.dependencies.auth import require_authenticated_user, require_module_access

from app.api.v1.routes import (
    assistant,
    backups,
    auth,
    bid_package,
    bid_readiness,
    bids,
    cost_codes,
    customer_quotes,
    daily_timesheets,
    documents,
    drawing_intelligence,
    employee_onboarding,
    employee_onboarding_portal,
    equipment,
    field_operations,
    finance,
    google_calendar,
    help_coach,
    estimates,
    media,
    municipality,
    meeting_minutes,
    operations,
    projects,
    quotes,
    rfq_automation,
    rfqs,
    suppliers,
    takeoff,
    tenders,
    users,
    workflow_drafts,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(
    employee_onboarding_portal.router,
    prefix="/employee-onboarding/portal",
    tags=["employee-onboarding-portal"],
)

protected_router = APIRouter(
    dependencies=[Depends(require_authenticated_user), Depends(require_module_access)]
)
protected_router.include_router(backups.router, prefix="/backups", tags=["backups"])
protected_router.include_router(projects.router, prefix="/projects", tags=["projects"])
protected_router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
protected_router.include_router(rfqs.router, prefix="/rfqs", tags=["rfqs"])
protected_router.include_router(rfq_automation.router, prefix="/rfq-automation", tags=["rfq-automation"])
protected_router.include_router(bid_package.router, prefix="/bid-package", tags=["bid-package"])
protected_router.include_router(bid_readiness.router, prefix="/bid-readiness", tags=["bid-readiness"])
protected_router.include_router(bids.router, prefix="/bids", tags=["bids"])
protected_router.include_router(estimates.router, prefix="/estimates", tags=["estimates"])
protected_router.include_router(cost_codes.router, prefix="/cost-codes", tags=["cost-codes"])
protected_router.include_router(
    customer_quotes.router,
    prefix="/customer-quotes",
    tags=["customer-quotes"],
)
protected_router.include_router(daily_timesheets.router, prefix="/daily-timesheets", tags=["daily-timesheets"])
protected_router.include_router(quotes.router, prefix="/quotes", tags=["quotes"])
protected_router.include_router(documents.router, prefix="/documents", tags=["documents"])
protected_router.include_router(
    drawing_intelligence.router,
    prefix="/drawing-intelligence",
    tags=["drawing-intelligence"],
)
protected_router.include_router(takeoff.router, prefix="/takeoff", tags=["takeoff"])
protected_router.include_router(municipality.router, prefix="/municipality", tags=["municipality"])
protected_router.include_router(tenders.router, prefix="/tenders", tags=["tenders"])
protected_router.include_router(equipment.router, prefix="/equipment", tags=["equipment"])
protected_router.include_router(field_operations.router, prefix="/field-operations", tags=["field-operations"])
protected_router.include_router(finance.router, prefix="/finance", tags=["finance"])
protected_router.include_router(media.router, prefix="/media", tags=["media"])
protected_router.include_router(help_coach.router, prefix="/help-coach", tags=["help-coach"])
protected_router.include_router(assistant.router, prefix="/iron-house-chat", tags=["iron-house-chat"])
protected_router.include_router(
    meeting_minutes.router,
    prefix="/meeting-minutes",
    tags=["meeting-minutes"],
)
protected_router.include_router(
    google_calendar.router,
    prefix="/google-calendar",
    tags=["google-calendar"],
)
protected_router.include_router(employee_onboarding.router, prefix="/employee-onboarding", tags=["employee-onboarding"])
protected_router.include_router(users.router, prefix="/users", tags=["users"])
protected_router.include_router(operations.router, prefix="/operations", tags=["operations"])
protected_router.include_router(
    workflow_drafts.router,
    prefix="/workflow-drafts",
    tags=["workflow-drafts"],
)
api_router.include_router(protected_router)
