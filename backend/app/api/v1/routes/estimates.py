from io import BytesIO
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.estimate import (
    EstimateCreate,
    EstimateHandoffRequest,
    EstimateHandoffResponse,
    EstimateLineItem,
    EstimateLineItemCost,
    EstimateSummary,
    RateLibrary,
)
from app.schemas.estimate_validation import EstimateValidationRequest, EstimateValidationResult
from app.schemas.estimate_workspace import EstimateWorkspaceList, EstimateWorkspaceRead, EstimateWorkspaceSaveRequest
from app.services import estimate_handoff, estimate_validation, estimate_workspace, estimate_workbooks, estimates

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


@router.get("/rate-library", response_model=RateLibrary)
def get_rate_library() -> RateLibrary:
    return estimates.get_rate_library()


@router.post("/line-item", response_model=EstimateLineItemCost)
def calculate_line_item(payload: EstimateLineItem) -> EstimateLineItemCost:
    return estimates.calculate_line_item(payload)


@router.post("/validate", response_model=EstimateValidationResult)
def validate_estimate(payload: EstimateValidationRequest) -> EstimateValidationResult:
    return estimate_validation.validate_estimate(payload)


@router.post("/handoff", response_model=EstimateHandoffResponse)
def build_handoff(payload: EstimateHandoffRequest) -> EstimateHandoffResponse:
    return estimate_handoff.build_estimate_handoff(payload)


@router.post("/workspace", response_model=EstimateWorkspaceRead, status_code=status.HTTP_201_CREATED)
def save_workspace(payload: EstimateWorkspaceSaveRequest, db: DBSession) -> EstimateWorkspaceRead:
    return estimate_workspace.save_workspace(db, payload)


@router.get("/workspace/project/{project_id}", response_model=EstimateWorkspaceList)
def list_project_workspaces(project_id: UUID, db: DBSession) -> EstimateWorkspaceList:
    return estimate_workspace.list_project_workspaces(db, project_id)


@router.get("/workspace/{workspace_id}", response_model=EstimateWorkspaceRead)
def read_workspace(workspace_id: UUID, db: DBSession) -> EstimateWorkspaceRead:
    return estimate_workspace.get_workspace(db, workspace_id)


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
