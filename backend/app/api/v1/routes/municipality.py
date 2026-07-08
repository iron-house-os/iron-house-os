from fastapi import APIRouter

from app.schemas.municipality import MunicipalityCheckRequest, MunicipalityCheckResponse
from app.services.municipality import check_municipality

router = APIRouter()


@router.post("/check", response_model=MunicipalityCheckResponse)
def check(payload: MunicipalityCheckRequest) -> MunicipalityCheckResponse:
    return check_municipality(payload)
