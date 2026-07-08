from fastapi import APIRouter

from app.schemas.rfq_automation import RFQAutomationRequest, RFQAutomationResponse
from app.services.rfq_automation import recommend_rfq_scopes

router = APIRouter()


@router.post("/recommend", response_model=RFQAutomationResponse)
def recommend(payload: RFQAutomationRequest) -> RFQAutomationResponse:
    return recommend_rfq_scopes(payload)
