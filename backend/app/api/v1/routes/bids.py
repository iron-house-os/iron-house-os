from fastapi import APIRouter

from app.api.v1.routes.common import PlaceholderList, placeholder_list
from app.schemas.estimate import EstimateCreate, EstimateSummary
from app.services import estimates

router = APIRouter()


@router.get("", response_model=PlaceholderList)
def list_bids() -> PlaceholderList:
    return placeholder_list("bids")


@router.post("/estimate-summary", response_model=EstimateSummary)
def calculate_estimate_summary(payload: EstimateCreate) -> EstimateSummary:
    return estimates.calculate_estimate(payload)
