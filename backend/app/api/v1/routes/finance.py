import csv
import io
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.db.session import get_db
from app.schemas.backups import BackupsIntakeList, BackupsReviewDestination
from app.schemas.chat_invoice_intake import ChatInvoiceIntakeRequest, ChatInvoiceIntakeResponse
from app.schemas.receipt import (
    ReceiptAction, ReceiptCreate, ReceiptExtractionRequest, ReceiptExtractionResponse,
    ReceiptList, ReceiptRead, ReceiptUpdate,
)
from app.schemas.finance import (
    CompletedWorkCostCreate,
    CompletedWorkCostCreateResult,
    CompletedWorkCostLedger,
    CustomerInvoiceCreate,
    CustomerInvoiceList,
    CustomerInvoiceRead,
    CustomerInvoiceStatusUpdate,
    EstimateBudgetImportRequest,
    FinancialEntryCreate,
    FinancialEntryRead,
    ProjectFinancialSummary,
    StartupExpenseCreate,
    StartupExpenseRead,
    StartupExpenseSummary,
    StartupExpenseUpdate,
)
from app.schemas.project_invoice_package import (
    ProjectInvoicePackageCreate,
    ProjectInvoicePackageReadiness,
    ProjectInvoicePackageResult,
)
from app.services import (
    backups,
    chat_invoice_intake,
    customer_invoices,
    completed_work_costs,
    finance,
    project_invoice_packages,
    receipt_extraction,
    receipts,
)
from app.services.customer_invoice_pdf import render_customer_invoice_pdf

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]


@router.post("/customer-invoices", response_model=CustomerInvoiceRead, status_code=status.HTTP_201_CREATED)
def create_customer_invoice(payload: CustomerInvoiceCreate, db: DBSession, user: CurrentUser) -> CustomerInvoiceRead:
    return customer_invoices.create_invoice(db, payload, user)


@router.post("/customer-invoices/chat-intake", response_model=ChatInvoiceIntakeResponse)
def chat_customer_invoice_intake(
    payload: ChatInvoiceIntakeRequest,
    db: DBSession,
    user: CurrentUser,
) -> ChatInvoiceIntakeResponse:
    return chat_invoice_intake.import_chat_invoices(db, payload, user)


@router.get("/customer-invoices", response_model=CustomerInvoiceList)
def list_customer_invoices(db: DBSession, user: CurrentUser) -> CustomerInvoiceList:
    return customer_invoices.list_invoices(db, user)


@router.get("/customer-invoices/{invoice_id}", response_model=CustomerInvoiceRead)
def get_customer_invoice(invoice_id: UUID, db: DBSession, user: CurrentUser) -> CustomerInvoiceRead:
    return customer_invoices.get_invoice(db, invoice_id, user)


@router.patch("/customer-invoices/{invoice_id}/status", response_model=CustomerInvoiceRead)
def update_customer_invoice_status(invoice_id: UUID, payload: CustomerInvoiceStatusUpdate, db: DBSession, user: CurrentUser) -> CustomerInvoiceRead:
    return customer_invoices.update_status(db, invoice_id, payload, user)


@router.get("/customer-invoices/{invoice_id}/pdf")
def customer_invoice_pdf(invoice_id: UUID, db: DBSession, user: CurrentUser) -> Response:
    invoice = customer_invoices.get_invoice(db, invoice_id, user)
    return Response(content=render_customer_invoice_pdf(invoice), media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{invoice.invoice_number}.pdf"'})


@router.get("/backups-review", response_model=BackupsIntakeList)
def backups_review_queue(
    destination: BackupsReviewDestination,
    db: DBSession,
    user: CurrentUser,
) -> BackupsIntakeList:
    return backups.list_finance_review_queue(db, user, destination)


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


@router.get(
    "/projects/{project_id}/completed-work-costs",
    response_model=CompletedWorkCostLedger,
)
def completed_work_cost_ledger(
    project_id: UUID,
    db: DBSession,
    user: CurrentUser,
) -> CompletedWorkCostLedger:
    return completed_work_costs.get_ledger(db, project_id, user)


@router.post(
    "/projects/{project_id}/completed-work-costs",
    response_model=CompletedWorkCostCreateResult,
)
def create_completed_work_cost(
    project_id: UUID,
    payload: CompletedWorkCostCreate,
    db: DBSession,
    user: CurrentUser,
) -> CompletedWorkCostCreateResult:
    return completed_work_costs.create_cost(db, project_id, payload, user)


@router.get(
    "/projects/{project_id}/invoice-package-readiness",
    response_model=ProjectInvoicePackageReadiness,
)
def project_invoice_package_readiness(
    project_id: UUID,
    db: DBSession,
    user: CurrentUser,
) -> ProjectInvoicePackageReadiness:
    return project_invoice_packages.get_readiness(db, project_id, user)


@router.post(
    "/projects/{project_id}/invoice-package",
    response_model=ProjectInvoicePackageResult,
)
def generate_project_invoice_package(
    project_id: UUID,
    payload: ProjectInvoicePackageCreate,
    db: DBSession,
    user: CurrentUser,
) -> ProjectInvoicePackageResult:
    return project_invoice_packages.generate_package(db, project_id, payload, user)


@router.get("/projects/{project_id}", response_model=ProjectFinancialSummary)
def project_financials(project_id: UUID, db: DBSession, user: CurrentUser) -> ProjectFinancialSummary:
    return finance.project_summary(db, project_id, user)


@router.get("/projects/{project_id}/quickbooks.csv")
def quickbooks_export(project_id: UUID, db: DBSession, user: CurrentUser) -> Response:
    buffer = io.StringIO()
    csv.writer(buffer).writerows(finance.quickbooks_rows(db, project_id, user))
    return Response(content=buffer.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="ihos-project-{project_id}-quickbooks.csv"'})
