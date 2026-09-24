from datetime import datetime

from pydantic import BaseModel


class QuickBooksStatus(BaseModel):
    enabled: bool
    configured: bool
    connected: bool
    status: str
    environment: str
    required_scope: str
    realm_id: str | None = None
    company_name: str | None = None
    legal_name: str | None = None
    last_verified_at: datetime | None = None
    last_error: str | None = None


class QuickBooksAuthorization(BaseModel):
    authorization_url: str


class QuickBooksDisconnect(BaseModel):
    confirmed: bool = False
