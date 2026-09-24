from datetime import datetime

from pydantic import BaseModel, SecretStr


class QuickBooksStatus(BaseModel):
    enabled: bool
    configured: bool
    database_configured: bool
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
    # Length checks are performed in the route and validation errors for this
    # endpoint are sanitized by the application exception handler. The latter is
    # required because Pydantic includes malformed input values in its default
    # response, including values that fail before route execution.
    client_id: str
    client_secret: SecretStr
    sandbox_confirmed: bool = False


class QuickBooksConfigurationRemove(BaseModel):
    confirmed: bool = False
