from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


FinancialEntryType = Literal["budget", "commitment", "actual", "revenue", "forecast_adjustment"]
FinancialCategory = Literal["labour", "equipment", "material", "trucking", "subcontract", "rental", "fuel", "overhead", "contingency", "bonding", "insurance", "other"]
StartupExpenseCategory = Literal["software", "office", "vehicle", "tools", "equipment", "professional", "insurance", "registration", "marketing", "communications", "other"]


class FinancialEntryCreate(BaseModel):
    project_id: UUID
    cost_code: str = Field(min_length=1, max_length=32)
    entry_type: FinancialEntryType
    category: FinancialCategory
    amount: float = Field(gt=0, le=999_999_999)
    entry_date: date
    vendor_name: str | None = Field(default=None, max_length=255)
    reference: str | None = Field(default=None, max_length=120)
    description: str | None = None
    status: Literal["draft", "open", "posted", "closed", "void"] = "posted"
    metadata_json: dict = Field(default_factory=dict)


class FinancialEntryRead(FinancialEntryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_type: str
    source_id: UUID | None
    created_by: str
    created_at: datetime
    updated_at: datetime


class StartupExpenseCreate(BaseModel):
    expense_date: date
    vendor_name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    amount: float = Field(gt=0, le=999_999_999)
    category: StartupExpenseCategory = "other"
    reference: str | None = Field(default=None, max_length=160)
    source_email: str | None = Field(default=None, max_length=255)
    funding_source: Literal["owner_loan", "company_paid"] = "owner_loan"
    owner_name: str | None = Field(default=None, max_length=255)
    tax_treatment: Literal["current_expense", "capital_asset", "needs_review"] = "needs_review"
    status: Literal["review", "approved", "reimbursed", "void"] = "review"
    receipt_metadata: dict = Field(default_factory=dict)


class StartupExpenseRead(StartupExpenseCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_by: str
    created_at: datetime
    updated_at: datetime


class StartupExpenseSummary(BaseModel):
    total_startup_costs: float
    owner_loan_payable: float
    reimbursed_to_owner: float
    pending_review: float
    approved_unreimbursed: float
    entries: list[StartupExpenseRead]


class StartupExpenseUpdate(BaseModel):
    status: Literal["review", "approved", "reimbursed", "void"] | None = None
    tax_treatment: Literal["current_expense", "capital_asset", "needs_review"] | None = None
    category: StartupExpenseCategory | None = None


class CostCodeFinancialSummary(BaseModel):
    cost_code: str
    budget: float
    committed: float
    actual: float
    forecast: float
    variance: float


class ProjectFinancialSummary(BaseModel):
    project_id: UUID
    project_name: str
    contract_value: float
    budget: float
    committed: float
    actual: float
    forecast_cost: float
    cost_variance: float
    forecast_profit: float
    forecast_margin_percent: float
    entries: list[FinancialEntryRead]
    cost_codes: list[CostCodeFinancialSummary]


class EstimateBudgetImportRequest(BaseModel):
    workspace_id: UUID | None = None


InvoiceStatus = Literal["draft", "approved", "issued", "paid", "void"]


class CustomerInvoiceLine(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    quantity: str = Field(default="1", min_length=1, max_length=30)
    unit_price: str = Field(min_length=1, max_length=30)


class CustomerInvoiceCreate(BaseModel):
    invoice_number: str = Field(min_length=1, max_length=80)
    project_id: UUID | None = None
    project_name: str = Field(min_length=1, max_length=255)
    site_address: str | None = Field(default=None, max_length=500)
    customer_name: str = Field(min_length=1, max_length=255)
    customer_address: str = Field(min_length=1, max_length=500)
    customer_phone: str | None = Field(default=None, max_length=40)
    invoice_date: date
    due_date: date
    terms: str = Field(default="Net 30", min_length=1, max_length=80)
    gst_rate: str = Field(default="5.00", min_length=1, max_length=20)
    line_items: list[CustomerInvoiceLine] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_dates(self) -> "CustomerInvoiceCreate":
        if self.due_date < self.invoice_date:
            raise ValueError("Due date cannot precede invoice date.")
        return self


class CustomerInvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    invoice_number: str
    project_id: UUID | None
    project_name: str
    site_address: str | None
    customer_name: str
    customer_address: str
    customer_phone: str | None
    invoice_date: date
    due_date: date
    terms: str
    status: InvoiceStatus
    line_items: list[dict]
    subtotal: str
    gst_rate: str
    gst: str
    total: str
    development_seed_key: str | None
    created_by: str
    issued_by: str | None
    issued_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CustomerInvoiceList(BaseModel):
    items: list[CustomerInvoiceRead]
    total: int


class CustomerInvoiceStatusUpdate(BaseModel):
    status: InvoiceStatus
