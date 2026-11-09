from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bid import Bid
from app.models.document import Document, Takeoff
from app.models.project import Project
from app.models.rfq import RFQPackage
from app.schemas.project_readiness import ProjectReadinessResponse, ReadinessItem


def get_project_readiness(db: Session, project_id: UUID) -> ProjectReadinessResponse:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    docs = db.scalars(select(Document).where(Document.project_id == project_id)).all()
    takeoffs = db.scalars(select(Takeoff).where(Takeoff.project_id == project_id)).all()
    bids = db.scalars(select(Bid).where(Bid.project_id == project_id)).all()
    rfq_packages = db.scalars(select(RFQPackage).where(RFQPackage.project_id == project_id)).all()

    items = [
        _item("Project setup", bool(project.name), f"Project status is {project.status}.", 1),
        _item("Tender dates", bool(project.bid_due_date or project.tender_closing_date), "Bid or tender closing date is recorded." if project.bid_due_date or project.tender_closing_date else "Missing bid/tender date.", 1),
        _item("Documents", bool(docs), f"{len(docs)} project documents registered.", 2),
        _item("Takeoffs", bool(takeoffs), f"{len(takeoffs)} saved takeoff records.", 2),
        _item("Estimate", bool(bids), f"{len(bids)} estimate/bid workspace records.", 1),
        _item("RFQ packages", bool(rfq_packages), f"{len(rfq_packages)} RFQ packages linked to project.", 2),
    ]
    ready_count = sum(1 for item in items if item.status == "ready")
    readiness_score = round(ready_count / len(items) * 100)
    blockers = [item.detail for item in items if item.status != "ready" and item.priority == 1]
    next_actions = [f"Complete: {item.label}" for item in items if item.status != "ready"]
    if not next_actions:
        next_actions.append("Project is ready for final bid review.")

    return ProjectReadinessResponse(
        project_id=project_id,
        readiness_score=readiness_score,
        status="ready" if readiness_score >= 85 and not blockers else "review",
        items=items,
        blockers=blockers,
        next_actions=next_actions,
    )


def _item(label: str, ready: bool, detail: str, priority: int) -> ReadinessItem:
    return ReadinessItem(label=label, status="ready" if ready else "review", detail=detail, priority=priority)
