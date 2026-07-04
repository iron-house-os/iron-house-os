from fastapi import APIRouter

from app.api.v1.routes import (
    auth,
    bids,
    documents,
    equipment,
    projects,
    rfqs,
    suppliers,
    tenders,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
api_router.include_router(rfqs.router, prefix="/rfqs", tags=["rfqs"])
api_router.include_router(bids.router, prefix="/bids", tags=["bids"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(tenders.router, prefix="/tenders", tags=["tenders"])
api_router.include_router(equipment.router, prefix="/equipment", tags=["equipment"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
