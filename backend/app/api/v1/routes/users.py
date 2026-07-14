from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import AdminUser
from app.db.session import get_db
from app.schemas.auth import (
    PasswordResetRequest,
    UserAccountCreate,
    UserAccountList,
    UserAccountRead,
    UserAccountUpdate,
)
from app.services import auth
from app.services.document_audit import DocumentAuditEvent, emit_document_audit_event
from app.services.request_context import get_request_audit_context

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


def _account_or_404(db: Session, account_id: UUID):
    account = auth.get_account(db, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")
    return account


@router.get("", response_model=UserAccountList)
def list_users(_: AdminUser, db: DBSession) -> UserAccountList:
    accounts = auth.list_accounts(db)
    return UserAccountList(
        items=[UserAccountRead.model_validate(account) for account in accounts],
        total=len(accounts),
    )


@router.post("", response_model=UserAccountRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserAccountCreate, _: AdminUser, db: DBSession) -> UserAccountRead:
    try:
        account = auth.create_account(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return UserAccountRead.model_validate(account)


@router.patch("/{account_id}", response_model=UserAccountRead)
def update_user(
    account_id: UUID,
    payload: UserAccountUpdate,
    admin: AdminUser,
    db: DBSession,
) -> UserAccountRead:
    account = _account_or_404(db, account_id)
    try:
        account = auth.update_account(db, account, payload, acting_user=admin)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return UserAccountRead.model_validate(account)


@router.post("/{account_id}/reset-password", response_model=UserAccountRead)
def reset_user_password(
    account_id: UUID,
    payload: PasswordResetRequest,
    request: Request,
    admin: AdminUser,
    db: DBSession,
) -> UserAccountRead:
    account = _account_or_404(db, account_id)
    recovered = auth.begin_admin_recovery(db, account, payload.password)
    context = get_request_audit_context(request)
    emit_document_audit_event(
        DocumentAuditEvent(
            action="account_recovery",
            actor=admin.email,
            request_id=context.request_id,
            metadata={"target_account_id": str(account.id)},
        )
    )
    return UserAccountRead.model_validate(recovered)
