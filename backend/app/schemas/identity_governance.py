from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class IdentityGovernanceSummary(BaseModel):
    total_accounts: int
    active_accounts: int
    active_administrators: int
    legacy_domain_accounts: int
    accounts_requiring_review: int
    critical_findings: int


class IdentityGovernanceAccount(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: str
    is_active: bool
    last_login_at: datetime | None
    password_reset_required: bool
    review_reasons: list[str]


class IdentityGovernanceFinding(BaseModel):
    code: str
    severity: Literal["critical", "high", "normal"]
    title: str
    recommendation: str
    account_ids: list[UUID]


class IdentityGovernanceSnapshot(BaseModel):
    generated_at: datetime
    canonical_email_domain: str
    summary: IdentityGovernanceSummary
    accounts: list[IdentityGovernanceAccount]
    findings: list[IdentityGovernanceFinding]
