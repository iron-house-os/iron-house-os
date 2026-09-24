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


class QuickBooksConfigurationWrite(BaseModel):
    # Length checks are intentionally performed in the route. Pydantic's default
    # validation response includes invalid input values, which must never echo a
    # Client Secret back to the browser.
    client_id: str
    client_secret: str
    sandbox_confirmed: bool = False


class QuickBooksConfigurationRemove(BaseModel):
    confirmed: bool = False
