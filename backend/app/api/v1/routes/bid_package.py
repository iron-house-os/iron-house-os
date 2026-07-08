from fastapi import APIRouter

from app.schemas.bid_package import BidPackageGenerateRequest, BidPackageGenerateResponse
from app.services.bid_package import generate_bid_package

router = APIRouter()


@router.post("/generate", response_model=BidPackageGenerateResponse)
def generate(payload: BidPackageGenerateRequest) -> BidPackageGenerateResponse:
    return generate_bid_package(payload)
