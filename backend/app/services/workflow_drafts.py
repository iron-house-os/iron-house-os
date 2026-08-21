from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.workflow_draft import WorkflowDraft
from app.schemas.workflow_draft import (
    WorkflowDraftCreate,
    WorkflowDraftList,
    WorkflowDraftRead,
    WorkflowDraftUpdate,
)


def _read(draft: WorkflowDraft) -> WorkflowDraftRead:
    return WorkflowDraftRead(
        id=draft.id,
        owner_account_id=draft.owner_account_id,
        project_id=draft.project_id,
        workflow_type=draft.workflow_type,
        title=draft.title,
        payload=draft.payload_json,
        schema_version=draft.schema_version,
        revision=draft.revision,
        status=draft.status,
        last_saved_at=draft.last_saved_at,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Workflow draft not found.",
    )


def _conflict() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="This draft changed in another session. Reload it before saving again.",
    )


def create_workflow_draft(
    db: Session,
    owner_account_id: UUID,
    payload: WorkflowDraftCreate,
) -> WorkflowDraftRead:
    now = datetime.now(UTC)
    draft = WorkflowDraft(
        owner_account_id=owner_account_id,
        project_id=payload.project_id,
        workflow_type=payload.workflow_type,
        title=payload.title.strip(),
        payload_json=payload.payload,
        schema_version=payload.schema_version,
        revision=1,
        status="active",
        last_saved_at=now,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return _read(draft)


def list_workflow_drafts(
    db: Session,
    owner_account_id: UUID,
    *,
    workflow_type: str | None = None,
    project_id: UUID | None = None,
    include_cancelled: bool = False,
) -> WorkflowDraftList:
    statement = select(WorkflowDraft).where(WorkflowDraft.owner_account_id == owner_account_id)
    if not include_cancelled:
        statement = statement.where(WorkflowDraft.status == "active")
    if workflow_type is not None:
        statement = statement.where(WorkflowDraft.workflow_type == workflow_type)
    if project_id is not None:
        statement = statement.where(WorkflowDraft.project_id == project_id)
    drafts = list(db.scalars(statement.order_by(WorkflowDraft.last_saved_at.desc())).all())
    return WorkflowDraftList(items=[_read(draft) for draft in drafts], total=len(drafts))


def get_workflow_draft(
    db: Session,
    owner_account_id: UUID,
    draft_id: UUID,
) -> WorkflowDraftRead:
    draft = db.scalar(
        select(WorkflowDraft).where(
            WorkflowDraft.id == draft_id,
            WorkflowDraft.owner_account_id == owner_account_id,
        )
    )
    if draft is None:
        raise _not_found()
    return _read(draft)


def update_workflow_draft(
    db: Session,
    owner_account_id: UUID,
    draft_id: UUID,
    payload: WorkflowDraftUpdate,
) -> WorkflowDraftRead:
    values: dict[str, object] = {
        "revision": WorkflowDraft.revision + 1,
        "last_saved_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    if "title" in payload.model_fields_set and payload.title is not None:
        values["title"] = payload.title.strip()
    if "payload" in payload.model_fields_set and payload.payload is not None:
        values["payload_json"] = payload.payload
    if "project_id" in payload.model_fields_set:
        values["project_id"] = payload.project_id
    if "schema_version" in payload.model_fields_set and payload.schema_version is not None:
        values["schema_version"] = payload.schema_version

    draft = db.scalar(
        update(WorkflowDraft)
        .where(
            WorkflowDraft.id == draft_id,
            WorkflowDraft.owner_account_id == owner_account_id,
            WorkflowDraft.status == "active",
            WorkflowDraft.revision == payload.expected_revision,
        )
        .values(**values)
        .returning(WorkflowDraft)
    )
    if draft is None:
        exists = db.scalar(
            select(WorkflowDraft.id).where(
                WorkflowDraft.id == draft_id,
                WorkflowDraft.owner_account_id == owner_account_id,
                WorkflowDraft.status == "active",
            )
        )
        raise _conflict() if exists is not None else _not_found()
    db.commit()
    db.refresh(draft)
    return _read(draft)


def transition_workflow_draft(
    db: Session,
    owner_account_id: UUID,
    draft_id: UUID,
    expected_revision: int,
    transition_status: str,
) -> WorkflowDraftRead:
    now = datetime.now(UTC)
    draft = db.scalar(
        update(WorkflowDraft)
        .where(
            WorkflowDraft.id == draft_id,
            WorkflowDraft.owner_account_id == owner_account_id,
            WorkflowDraft.status == "active",
            WorkflowDraft.revision == expected_revision,
        )
        .values(
            status=transition_status,
            revision=WorkflowDraft.revision + 1,
            last_saved_at=now,
            updated_at=now,
        )
        .returning(WorkflowDraft)
    )
    if draft is None:
        exists = db.scalar(
            select(WorkflowDraft.id).where(
                WorkflowDraft.id == draft_id,
                WorkflowDraft.owner_account_id == owner_account_id,
                WorkflowDraft.status == "active",
            )
        )
        raise _conflict() if exists is not None else _not_found()
    db.commit()
    db.refresh(draft)
    return _read(draft)
