from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.bid import Bid
from app.models.finance import FinancialEntry
from app.models.project import Project
from app.schemas.finance import EstimateBudgetImportRequest, FinancialEntryCreate, FinancialEntryRead, ProjectFinancialSummary, CostCodeFinancialSummary
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
    summary = bid.bid_json["summary"]
    db.execute(delete(FinancialEntry).where(FinancialEntry.project_id == project_id, FinancialEntry.entry_type == "budget"))
    for line in summary.get("line_items") or []:
        amount = float(line.get("direct_cost") or 0)
        if amount <= 0:
            continue
        db.add(FinancialEntry(project_id=project_id, cost_code=str(line.get("code") or "UNALLOCATED"), entry_type="budget", category=_category(line.get("item_type")), amount=amount, entry_date=date.today(), description=str(line.get("description") or "Estimate budget line"), source_type="estimate_workspace", source_id=bid.id, status="posted", metadata_json={"workspace_id": str(bid.id)}, created_by=user.email))
    extras = [("90-100", "overhead", summary.get("indirect_cost", 0), "Indirect costs"), ("90-200", "contingency", summary.get("risk_cost", 0), "Risk allowance"), ("90-300", "contingency", summary.get("contingency", 0), "Contingency"), ("90-400", "bonding", summary.get("bonding", 0), "Bonding"), ("90-500", "insurance", summary.get("insurance", 0), "Insurance"), ("90-600", "overhead", summary.get("overhead", 0), "Corporate overhead")]
    for cost_code, category, amount, description in extras:
        if float(amount or 0) > 0:
            db.add(FinancialEntry(project_id=project_id, cost_code=cost_code, entry_type="budget", category=category, amount=float(amount), entry_date=date.today(), description=description, source_type="estimate_workspace", source_id=bid.id, status="posted", metadata_json={"workspace_id": str(bid.id)}, created_by=user.email))
    if project.contract_value is None and summary.get("final_price"):
        project.contract_value = float(summary["final_price"])
        db.add(project)
    db.commit()
    return project_summary(db, project_id, user)


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


def _total(entries: list[FinancialEntry], entry_type: str) -> float:
    return round(sum(float(x.amount) for x in entries if x.entry_type == entry_type), 2)


def _category(item_type: object) -> str:
    value = str(item_type or "other")
    return value if value in {"labour", "equipment", "material", "subcontract"} else "other"
