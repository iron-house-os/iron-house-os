from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.db.session import get_db
from app.schemas.workflow_draft import (
    WorkflowDraftCreate,
    WorkflowDraftList,
    WorkflowDraftRead,
    WorkflowDraftUpdate,
    WorkflowDraftTransition,
    WorkflowType,
)
from app.services import workflow_drafts

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]
OptionalWorkflowType = Annotated[WorkflowType | None, Query()]
OptionalProjectId = Annotated[UUID | None, Query()]


@router.post("", response_model=WorkflowDraftRead, status_code=status.HTTP_201_CREATED)
def create_workflow_draft(
    payload: WorkflowDraftCreate,
    user: CurrentUser,
    db: DBSession,
) -> WorkflowDraftRead:
    return workflow_drafts.create_workflow_draft(db, user.id, payload)


@router.get("", response_model=WorkflowDraftList)
def list_workflow_drafts(
    user: CurrentUser,
    db: DBSession,
    workflow_type: OptionalWorkflowType = None,
    project_id: OptionalProjectId = None,
    include_cancelled: bool = False,
) -> WorkflowDraftList:
    return workflow_drafts.list_workflow_drafts(
        db,
        user.id,
        workflow_type=workflow_type,
        project_id=project_id,
        include_cancelled=include_cancelled,
    )


@router.get("/{draft_id}", response_model=WorkflowDraftRead)
def read_workflow_draft(
    draft_id: UUID,
    user: CurrentUser,
    db: DBSession,
) -> WorkflowDraftRead:
    return workflow_drafts.get_workflow_draft(db, user.id, draft_id)


@router.patch("/{draft_id}", response_model=WorkflowDraftRead)
def update_workflow_draft(
    draft_id: UUID,
    payload: WorkflowDraftUpdate,
    user: CurrentUser,
    db: DBSession,
) -> WorkflowDraftRead:
    return workflow_drafts.update_workflow_draft(db, user.id, draft_id, payload)


@router.post("/{draft_id}/cancel", response_model=WorkflowDraftRead)
def cancel_workflow_draft(
    draft_id: UUID,
    payload: WorkflowDraftTransition,
    user: CurrentUser,
    db: DBSession,
) -> WorkflowDraftRead:
    return workflow_drafts.transition_workflow_draft(
        db,
        user.id,
        draft_id,
        payload.expected_revision,
        "cancelled",
    )


@router.post("/{draft_id}/complete", response_model=WorkflowDraftRead)
def complete_workflow_draft(
    draft_id: UUID,
    payload: WorkflowDraftTransition,
    user: CurrentUser,
    db: DBSession,
) -> WorkflowDraftRead:
    return workflow_drafts.transition_workflow_draft(
        db,
        user.id,
        draft_id,
        payload.expected_revision,
        "completed",
    )
