import csv
import io
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.db.session import get_db
from app.schemas.receipt import (
    ReceiptAction, ReceiptCreate, ReceiptExtractionRequest, ReceiptExtractionResponse,
    ReceiptList, ReceiptRead, ReceiptUpdate,
)
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
from app.services import finance, receipt_extraction, receipts

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


@router.post("/receipts", response_model=ReceiptRead, status_code=status.HTTP_201_CREATED)
def create_receipt(payload: ReceiptCreate, db: DBSession, user: CurrentUser) -> ReceiptRead:
    return receipts.create_receipt(db, payload, user)


@router.get("/receipts", response_model=ReceiptList)
def list_receipts(db: DBSession, user: CurrentUser, receipt_status: str | None = None) -> ReceiptList:
    return receipts.list_receipts(db, user, receipt_status)


@router.post("/receipts/extract", response_model=ReceiptExtractionResponse)
def extract_receipt(payload: ReceiptExtractionRequest, db: DBSession, user: CurrentUser) -> ReceiptExtractionResponse:
    return receipt_extraction.extract_receipt(db, payload, user)


@router.get("/receipts/{receipt_id}", response_model=ReceiptRead)
def get_receipt(receipt_id: UUID, db: DBSession, user: CurrentUser) -> ReceiptRead:
    return receipts.get_receipt(db, receipt_id, user)


@router.put("/receipts/{receipt_id}", response_model=ReceiptRead)
def update_receipt(receipt_id: UUID, payload: ReceiptUpdate, db: DBSession, user: CurrentUser) -> ReceiptRead:
    return receipts.update_receipt(db, receipt_id, payload, user)


@router.post("/receipts/{receipt_id}/submit", response_model=ReceiptRead)
def submit_receipt(receipt_id: UUID, payload: ReceiptAction, db: DBSession, user: CurrentUser) -> ReceiptRead:
    return receipts.submit_receipt(db, receipt_id, payload, user)


@router.post("/receipts/{receipt_id}/approve", response_model=ReceiptRead)
def approve_receipt(receipt_id: UUID, payload: ReceiptAction, db: DBSession, user: CurrentUser) -> ReceiptRead:
    return receipts.approve_receipt(db, receipt_id, payload, user)


@router.post("/receipts/{receipt_id}/export")
def export_receipt(receipt_id: UUID, payload: ReceiptAction, db: DBSession, user: CurrentUser) -> Response:
    content = receipts.export_receipt(db, receipt_id, payload, user)
    return Response(content=content, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="ihos-receipt-{receipt_id}.csv"'})


@router.post("/receipts/{receipt_id}/reconcile", response_model=ReceiptRead)
def reconcile_receipt(receipt_id: UUID, payload: ReceiptAction, db: DBSession, user: CurrentUser) -> ReceiptRead:
    return receipts.reconcile_receipt(db, receipt_id, payload, user)


@router.post("/receipts/{receipt_id}/void", response_model=ReceiptRead)
def void_receipt(receipt_id: UUID, payload: ReceiptAction, db: DBSession, user: CurrentUser) -> ReceiptRead:
    return receipts.void_receipt(db, receipt_id, payload, user)


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
