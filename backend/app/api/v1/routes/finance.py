import csv
import io
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.db.session import get_db
from app.schemas.finance import (
    EstimateBudgetImportRequest,
    FinancialEntryCreate,
    FinancialEntryRead,
    ProjectFinancialSummary,
    StartupExpenseCreate,
    StartupExpenseRead,
    StartupExpenseSummary,
    StartupExpenseUpdate,
)
from app.services import finance

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


@router.post("/entries", response_model=FinancialEntryRead, status_code=status.HTTP_201_CREATED)
def create_entry(payload: FinancialEntryCreate, db: DBSession, user: CurrentUser) -> FinancialEntryRead:
    return finance.create_entry(db, payload, user)


@router.post("/startup-expenses", response_model=StartupExpenseRead, status_code=status.HTTP_201_CREATED)
def create_startup_expense(payload: StartupExpenseCreate, db: DBSession, user: CurrentUser) -> StartupExpenseRead:
    return finance.create_startup_expense(db, payload, user)


@router.patch("/startup-expenses/{expense_id}", response_model=StartupExpenseRead)
def update_startup_expense(expense_id: UUID, payload: StartupExpenseUpdate, db: DBSession, user: CurrentUser) -> StartupExpenseRead:
    return finance.update_startup_expense(db, expense_id, payload, user)


@router.get("/startup-expenses", response_model=StartupExpenseSummary)
def startup_expenses(db: DBSession, user: CurrentUser) -> StartupExpenseSummary:
    return finance.startup_expense_summary(db, user)


@router.get("/startup-expenses/quickbooks.csv")
def startup_quickbooks_export(db: DBSession, user: CurrentUser) -> Response:
    buffer = io.StringIO()
    csv.writer(buffer).writerows(finance.startup_quickbooks_rows(db, user))
    return Response(content=buffer.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="ihos-startup-owner-loan.csv"'})


@router.post("/projects/{project_id}/import-estimate", response_model=ProjectFinancialSummary)
def import_estimate(project_id: UUID, payload: EstimateBudgetImportRequest, db: DBSession, user: CurrentUser) -> ProjectFinancialSummary:
    return finance.import_estimate_budget(db, project_id, payload, user)


@router.get("/projects/{project_id}", response_model=ProjectFinancialSummary)
def project_financials(project_id: UUID, db: DBSession, user: CurrentUser) -> ProjectFinancialSummary:
    return finance.project_summary(db, project_id, user)


@router.get("/projects/{project_id}/quickbooks.csv")
def quickbooks_export(project_id: UUID, db: DBSession, user: CurrentUser) -> Response:
    buffer = io.StringIO()
    csv.writer(buffer).writerows(finance.quickbooks_rows(db, project_id, user))
    return Response(content=buffer.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="ihos-project-{project_id}-quickbooks.csv"'})
