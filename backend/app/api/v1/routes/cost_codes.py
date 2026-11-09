from fastapi import APIRouter

from app.schemas.cost_code import CostCodeLibrary, CostCodeResolveRequest, CostCodeResolveResponse
from app.services import cost_codes

router = APIRouter()


@router.get("", response_model=CostCodeLibrary)
def list_cost_codes() -> CostCodeLibrary:
    return cost_codes.get_cost_code_library()


@router.post("/resolve", response_model=CostCodeResolveResponse)
def resolve_cost_code(payload: CostCodeResolveRequest) -> CostCodeResolveResponse:
    return cost_codes.resolve_cost_code(payload)
