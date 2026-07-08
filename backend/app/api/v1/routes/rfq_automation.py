from fastapi import APIRouter

from app.schemas.rfq_automation import RFQAutomationRequest, RFQAutomationResponse
from app.schemas.rfq_linkage import RFQLinkageRequest, RFQLinkageResponse
from app.services.rfq_automation import recommend_rfq_scopes
from app.services.rfq_linkage import build_rfq_package_drafts

router = APIRouter()


@router.post("/recommend", response_model=RFQAutomationResponse)
def recommend(payload: RFQAutomationRequest) -> RFQAutomationResponse:
    return recommend_rfq_scopes(payload)


@router.post("/linkage", response_model=RFQLinkageResponse)
def linkage(payload: RFQLinkageRequest) -> RFQLinkageResponse:
    return build_rfq_package_drafts(payload)
