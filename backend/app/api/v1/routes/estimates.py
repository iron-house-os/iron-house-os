from fastapi import APIRouter

from app.schemas.estimate import (
    EstimateCreate,
    EstimateLineItem,
    EstimateLineItemCost,
    EstimateSummary,
    RateLibrary,
)
from app.services import estimates

router = APIRouter()


@router.get("/rate-library", response_model=RateLibrary)
def get_rate_library() -> RateLibrary:
    return estimates.get_rate_library()


@router.post("/line-item", response_model=EstimateLineItemCost)
def calculate_line_item(payload: EstimateLineItem) -> EstimateLineItemCost:
    return estimates.calculate_line_item(payload)


@router.post("/summary", response_model=EstimateSummary)
def calculate_estimate_summary(payload: EstimateCreate) -> EstimateSummary:
    return estimates.calculate_estimate(payload)
