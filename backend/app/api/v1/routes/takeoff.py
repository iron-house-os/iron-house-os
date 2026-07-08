from fastapi import APIRouter

from app.schemas.takeoff import QuantityRegisterRequest, QuantityRegisterResponse
from app.services.takeoff import summarize_quantity_register

router = APIRouter()


@router.post("/summarize", response_model=QuantityRegisterResponse)
def summarize(payload: QuantityRegisterRequest) -> QuantityRegisterResponse:
    return summarize_quantity_register(payload)
