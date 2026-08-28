from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bid import Bid
from app.models.finance import FinancialEntry, StartupExpense
from app.models.project import Project
from app.schemas.finance import (
    CostCodeFinancialSummary,
    EstimateBudgetImportRequest,
    FinancialEntryCreate,
    FinancialEntryRead,
    ProjectFinancialSummary,
    StartupExpenseCreate,
    StartupExpenseRead,
    StartupExpenseSummary,
    StartupExpenseUpdate,
)
from app.services.auth import AuthenticatedUser


MANAGEMENT_ROLES = {"admin", "operations_manager"}


def require_management(user: AuthenticatedUser) -> None:
    if user.role not in MANAGEMENT_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Management financial access is required.")


def create_entry(db: Session, payload: FinancialEntryCreate, user: AuthenticatedUser) -> FinancialEntryRead:
    require_management(user)
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    values = payload.model_dump()
    entry = FinancialEntry(**values, source_type="manual", created_by=user.email)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return FinancialEntryRead.model_validate(entry)


def create_startup_expense(db: Session, payload: StartupExpenseCreate, user: AuthenticatedUser) -> StartupExpenseRead:
    require_management(user)
    entry = StartupExpense(**payload.model_dump(), created_by=user.email)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return StartupExpenseRead.model_validate(entry)


def update_startup_expense(db: Session, expense_id: UUID, payload: StartupExpenseUpdate, user: AuthenticatedUser) -> StartupExpenseRead:
    require_management(user)
    entry = db.get(StartupExpense, expense_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Startup expense not found")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(entry, key, value)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return StartupExpenseRead.model_validate(entry)


def startup_expense_summary(db: Session, user: AuthenticatedUser) -> StartupExpenseSummary:
    require_management(user)
    entries = list(db.scalars(select(StartupExpense).where(StartupExpense.status != "void").order_by(StartupExpense.expense_date.desc(), StartupExpense.created_at.desc())))
    active = [entry for entry in entries if entry.status in {"review", "approved", "reimbursed"}]
    owner_funded = [entry for entry in active if entry.funding_source == "owner_loan"]
    total = round(sum(float(entry.amount) for entry in active), 2)
    reimbursed = round(sum(float(entry.amount) for entry in owner_funded if entry.status == "reimbursed"), 2)
    owner_loan_payable = round(sum(float(entry.amount) for entry in owner_funded if entry.status in {"review", "approved"}), 2)
    pending = round(sum(float(entry.amount) for entry in active if entry.status == "review"), 2)
    approved = round(sum(float(entry.amount) for entry in owner_funded if entry.status == "approved"), 2)
    return StartupExpenseSummary(total_startup_costs=total, owner_loan_payable=owner_loan_payable, reimbursed_to_owner=reimbursed, pending_review=pending, approved_unreimbursed=approved, entries=[StartupExpenseRead.model_validate(entry) for entry in entries])


def import_estimate_budget(db: Session, project_id: UUID, payload: EstimateBudgetImportRequest, user: AuthenticatedUser) -> ProjectFinancialSummary:
    require_management(user)
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    query = select(Bid).where(Bid.project_id == project_id)
    if payload.workspace_id:
        query = query.where(Bid.id == payload.workspace_id)
    bid = db.scalar(query.order_by(Bid.updated_at.desc()))
    if bid is None or not (bid.bid_json or {}).get("summary"):
        raise HTTPException(status_code=400, detail="Save a priced estimate workspace before creating the project budget.")
    specs = _estimate_budget_specs(bid, payload)
    all_budget_entries = list(
        db.scalars(
            select(FinancialEntry).where(
                FinancialEntry.project_id == project_id,
                FinancialEntry.entry_type == "budget",
            )
        )
    )
    existing = [entry for entry in all_budget_entries if entry.status != "void"]
    conflicting = [
        entry
        for entry in existing
        if entry.source_type != "estimate_workspace" or entry.source_id != bid.id
    ]
    if conflicting:
        raise HTTPException(
            status_code=409,
            detail="A manual or different-workspace budget already exists. Review it before importing.",
        )
    legacy = [entry for entry in existing if not entry.source_key]
    for entry in legacy:
        db.delete(entry)
    keyed = {
        entry.source_key: entry
        for entry in all_budget_entries
        if entry.source_type == "estimate_workspace"
        and entry.source_id == bid.id
        and entry.source_key
    }
    expected_keys = {spec["source_key"] for spec in specs}
    for source_key, entry in keyed.items():
        if source_key not in expected_keys:
            entry.status = "void"
    for spec in specs:
        entry = keyed.get(spec["source_key"])
        values = {
            "cost_code": spec["cost_code"],
            "category": spec["category"],
            "amount": spec["amount"],
            "entry_date": date.today(),
            "description": spec["description"],
            "source_type": "estimate_workspace",
            "source_id": bid.id,
            "source_key": spec["source_key"],
            "status": "posted",
            "metadata_json": {
                "workspace_id": str(bid.id),
                "source_code": spec["source_code"],
                "cost_code_name": spec["cost_code_name"],
            },
            "created_by": user.email,
        }
        if entry is None:
            db.add(FinancialEntry(project_id=project_id, entry_type="budget", **values))
        else:
            for key, value in values.items():
                setattr(entry, key, value)

    metadata = dict(project.metadata_json or {})
    baseline = dict(metadata.get("award_pricing_baseline") or {})
    budget_lines = [
        {
            "source_key": spec["source_key"],
            "source_code": spec["source_code"],
            "cost_code": spec["cost_code"],
            "cost_code_name": spec["cost_code_name"],
            "category": spec["category"],
            "description": spec["description"],
            "amount": f'{spec["amount"]:.2f}',
        }
        for spec in specs
    ]
    baseline.update(
        {
            "cost_budget_status": "allocated",
            "cost_budget_source_workspace_id": str(bid.id),
            "cost_budget_total": f'{sum(spec["amount"] for spec in specs):.2f}',
            "cost_budget_lines": budget_lines,
        }
    )
    metadata["award_pricing_baseline"] = baseline
    cost_codes: dict[str, dict[str, str]] = {}
    for spec in specs:
        cost_codes[spec["cost_code"]] = {
            "code": spec["cost_code"],
            "name": spec["cost_code_name"],
        }
    metadata["project_cost_codes"] = list(cost_codes.values())
    project.metadata_json = metadata
    summary = bid.bid_json["summary"]
    if project.contract_value is None and summary.get("final_price"):
        project.contract_value = float(summary["final_price"])
        db.add(project)
    db.commit()
    return project_summary(db, project_id, user)


def _estimate_budget_specs(bid: Bid, payload: EstimateBudgetImportRequest) -> list[dict]:
    bid_json = bid.bid_json or {}
    summary = bid_json.get("summary") or {}
    estimate = bid_json.get("estimate") or {}
    mappings = {str(key).strip().upper(): str(value).strip().upper() for key, value in payload.cost_code_mappings.items()}
    names = {str(key).strip().upper(): str(value).strip() for key, value in payload.cost_code_names.items()}
    specs: list[dict] = []

    def add(
        *,
        position: str,
        source_code: str,
        default_code: str,
        category: str,
        amount: object,
        description: str,
        override_code: str | None = None,
        override_name: str | None = None,
    ) -> None:
        numeric = round(float(amount or 0), 2)
        if numeric <= 0:
            return
        normalized_source = source_code.strip().upper()
        cost_code = (override_code or mappings.get(normalized_source) or default_code).strip().upper()
        if not cost_code:
            cost_code = "UNALLOCATED"
        specs.append(
            {
                "source_key": f"estimate-budget:{bid.id}:{position}",
                "source_code": normalized_source,
                "cost_code": cost_code,
                "cost_code_name": (override_name or names.get(cost_code) or description).strip(),
                "category": category,
                "amount": numeric,
                "description": description.strip(),
            }
        )

    for index, line in enumerate(summary.get("line_items") or [], start=1):
        source_code = str(line.get("code") or f"LINE-{index:03d}")
        add(
            position=f"line-{index:03d}",
            source_code=source_code,
            default_code=source_code,
            category=_category(line.get("item_type")),
            amount=line.get("direct_cost"),
            description=str(line.get("description") or "Estimate budget line"),
        )

    risk_amount = float(summary.get("risk_cost") or 0)
    risks = estimate.get("risks") or []
    if len(risks) == 1:
        risk_description = str(risks[0].get("description") or "Risk allowance")
    else:
        risk_description = "Risk allowance"
    add(
        position="risk",
        source_code="RISK",
        default_code="90-200",
        category="contingency",
        amount=risk_amount,
        description=risk_description,
        override_code=payload.risk_cost_code,
        override_name=payload.risk_cost_code_name,
    )
    extras = [
        ("indirect", "INDIRECT", "90-100", "overhead", summary.get("indirect_cost", 0), "Indirect costs"),
        ("contingency", "CONTINGENCY", "90-300", "contingency", summary.get("contingency", 0), "Contingency"),
        ("bonding", "BONDING", "90-400", "bonding", summary.get("bonding", 0), "Bonding"),
        ("insurance", "INSURANCE", "90-500", "insurance", summary.get("insurance", 0), "Insurance"),
        ("overhead", "OVERHEAD", "90-600", "overhead", summary.get("overhead", 0), "Corporate overhead"),
    ]
    for position, source_code, cost_code, category, amount, description in extras:
        add(
            position=position,
            source_code=source_code,
            default_code=cost_code,
            category=category,
            amount=amount,
            description=description,
        )
    if not specs:
        raise HTTPException(status_code=400, detail="The selected estimate has no cost basis to import.")
    return specs


def project_summary(db: Session, project_id: UUID, user: AuthenticatedUser) -> ProjectFinancialSummary:
    require_management(user)
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    entries = list(db.scalars(select(FinancialEntry).where(FinancialEntry.project_id == project_id, FinancialEntry.status != "void").order_by(FinancialEntry.entry_date.desc(), FinancialEntry.created_at.desc())))
    budget = _total(entries, "budget")
    committed = sum(float(x.amount) for x in entries if x.entry_type == "commitment" and x.status in {"open", "posted"})
    actual = _total(entries, "actual")
    adjustments = _total(entries, "forecast_adjustment")
    forecast = actual + committed + adjustments
    contract = _total(entries, "revenue") or float(project.contract_value or 0)
    profit = contract - forecast
    codes = []
    for code in sorted({x.cost_code for x in entries}):
        rows = [x for x in entries if x.cost_code == code]
        code_budget = _total(rows, "budget")
        code_committed = sum(float(x.amount) for x in rows if x.entry_type == "commitment" and x.status in {"open", "posted"})
        code_actual = _total(rows, "actual")
        code_forecast = code_actual + code_committed + _total(rows, "forecast_adjustment")
        codes.append(CostCodeFinancialSummary(cost_code=code, budget=code_budget, committed=code_committed, actual=code_actual, forecast=code_forecast, variance=code_budget-code_forecast))
    return ProjectFinancialSummary(project_id=project.id, project_name=project.name, contract_value=contract, budget=budget, committed=committed, actual=actual, forecast_cost=forecast, cost_variance=budget-forecast, forecast_profit=profit, forecast_margin_percent=round(profit/contract*100, 2) if contract else 0, entries=[FinancialEntryRead.model_validate(x) for x in entries], cost_codes=codes)


def quickbooks_rows(db: Session, project_id: UUID, user: AuthenticatedUser) -> list[list[str]]:
    summary = project_summary(db, project_id, user)
    rows = [["Date", "Reference", "Project", "Cost Code", "Category", "Type", "Vendor", "Description", "Amount CAD", "Status"]]
    for entry in summary.entries:
        if entry.entry_type == "budget":
            continue
        rows.append([entry.entry_date.isoformat(), entry.reference or "", summary.project_name, entry.cost_code, entry.category, entry.entry_type, entry.vendor_name or "", entry.description or "", f"{entry.amount:.2f}", entry.status])
    return rows


def startup_quickbooks_rows(db: Session, user: AuthenticatedUser) -> list[list[str]]:
    summary = startup_expense_summary(db, user)
    rows = [["Date", "Vendor", "Reference", "Description", "Category", "Expense", "Funding account", "Status", "Tax treatment"]]
    for entry in summary.entries:
        if entry.status == "void":
            continue
        rows.append([entry.expense_date.isoformat(), entry.vendor_name, entry.reference or "", entry.description, entry.category, f"{entry.amount:.2f}", "Owner/Shareholder Loan Payable" if entry.funding_source == "owner_loan" else "Company cash/bank", entry.status, entry.tax_treatment])
    return rows


def _total(entries: list[FinancialEntry], entry_type: str) -> float:
    return round(sum(float(x.amount) for x in entries if x.entry_type == entry_type), 2)


def _category(item_type: object) -> str:
    value = str(item_type or "other")
    return value if value in {"labour", "equipment", "material", "subcontract"} else "other"
