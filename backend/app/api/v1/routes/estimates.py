from io import BytesIO

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.estimate import (
    EstimateCreate,
    EstimateLineItem,
    EstimateLineItemCost,
    EstimateSummary,
    RateLibrary,
)
from app.services import estimate_workbooks, estimates

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


@router.post("/workbook")
def generate_estimate_workbook(payload: EstimateCreate) -> StreamingResponse:
    workbook_bytes = estimate_workbooks.build_estimate_workbook(payload)
    filename = estimate_workbooks.workbook_filename(payload.project_name, payload.project_code)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        BytesIO(workbook_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
