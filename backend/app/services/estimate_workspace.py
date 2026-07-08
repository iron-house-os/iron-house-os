from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bid import Bid
from app.models.project import Project
from app.schemas.estimate_workspace import EstimateWorkspaceList, EstimateWorkspaceRead, EstimateWorkspaceSaveRequest


def save_workspace(db: Session, payload: EstimateWorkspaceSaveRequest) -> EstimateWorkspaceRead:
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    total_amount = payload.summary.final_price if payload.summary else None
    summary_text = _summary_text(payload)
    bid_json = {
        "estimate": payload.estimate.model_dump(mode="json"),
        "summary": payload.summary.model_dump(mode="json") if payload.summary else None,
        "source": "estimate_workspace",
    }
    bid = Bid(
        project_id=payload.project_id,
        tender_id=payload.tender_id,
        status=payload.status,
        total_amount=total_amount,
        summary=summary_text,
        bid_json=bid_json,
    )
    db.add(bid)
    db.commit()
    db.refresh(bid)
    return _to_read(bid)


def list_project_workspaces(db: Session, project_id: UUID) -> EstimateWorkspaceList:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    rows = db.scalars(select(Bid).where(Bid.project_id == project_id).order_by(Bid.created_at.desc())).all()
    return EstimateWorkspaceList(items=[_to_read(row) for row in rows], total=len(rows))


def get_workspace(db: Session, workspace_id: UUID) -> EstimateWorkspaceRead:
    bid = db.get(Bid, workspace_id)
    if not bid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estimate workspace not found")
    return _to_read(bid)


def _summary_text(payload: EstimateWorkspaceSaveRequest) -> str:
    if not payload.summary:
        return f"Draft estimate with {len(payload.estimate.line_items)} line items."
    return f"Estimate total {payload.summary.final_price:.2f} with {len(payload.summary.line_items)} priced line items."


def _to_read(bid: Bid) -> EstimateWorkspaceRead:
    return EstimateWorkspaceRead(
        id=bid.id,
        project_id=bid.project_id,
        tender_id=bid.tender_id,
        status=bid.status,
        total_amount=float(bid.total_amount) if bid.total_amount is not None else None,
        summary_text=bid.summary,
        estimate=bid.bid_json or {},
        created_at=bid.created_at,
        updated_at=bid.updated_at,
    )
