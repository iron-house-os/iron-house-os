from fastapi import APIRouter

from app.schemas.takeoff import QuantityRegisterRequest, QuantityRegisterResponse, TakeoffEngineRequest, TakeoffEngineResponse
from app.services.takeoff import run_takeoff_engine, summarize_quantity_register

router = APIRouter()


@router.post("/summarize", response_model=QuantityRegisterResponse)
def summarize(payload: QuantityRegisterRequest) -> QuantityRegisterResponse:
    return summarize_quantity_register(payload)


@router.post("/engine", response_model=TakeoffEngineResponse)
def engine(payload: TakeoffEngineRequest) -> TakeoffEngineResponse:
    return run_takeoff_engine(payload)
