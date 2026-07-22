from fastapi import APIRouter, Depends

from app.api.dependencies.auth import require_authenticated_user, require_module_access

from app.api.v1.routes import (
    auth,
    bid_package,
    bid_readiness,
    bids,
    cost_codes,
    documents,
    drawing_intelligence,
    equipment,
    field_operations,
    estimates,
    municipality,
    operations,
    projects,
    quotes,
    rfq_automation,
    rfqs,
    suppliers,
    takeoff,
    tenders,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

protected_router = APIRouter(
    dependencies=[Depends(require_authenticated_user), Depends(require_module_access)]
)
protected_router.include_router(projects.router, prefix="/projects", tags=["projects"])
protected_router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
protected_router.include_router(rfqs.router, prefix="/rfqs", tags=["rfqs"])
protected_router.include_router(rfq_automation.router, prefix="/rfq-automation", tags=["rfq-automation"])
protected_router.include_router(bid_package.router, prefix="/bid-package", tags=["bid-package"])
protected_router.include_router(bid_readiness.router, prefix="/bid-readiness", tags=["bid-readiness"])
protected_router.include_router(bids.router, prefix="/bids", tags=["bids"])
protected_router.include_router(estimates.router, prefix="/estimates", tags=["estimates"])
protected_router.include_router(cost_codes.router, prefix="/cost-codes", tags=["cost-codes"])
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
protected_router.include_router(users.router, prefix="/users", tags=["users"])
protected_router.include_router(operations.router, prefix="/operations", tags=["operations"])
api_router.include_router(protected_router)
