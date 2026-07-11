from fastapi import APIRouter

from app.schemas.bid_readiness import BidReadinessRequest, BidReadinessResponse
from app.services.bid_readiness import evaluate_bid_readiness

router = APIRouter()


@router.post("/evaluate", response_model=BidReadinessResponse)
def evaluate(payload: BidReadinessRequest) -> BidReadinessResponse:
    return evaluate_bid_readiness(payload)
