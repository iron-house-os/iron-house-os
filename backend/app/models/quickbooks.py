from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JSONType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class QuickBooksConnection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quickbooks_connections"

    environment: Mapped[str] = mapped_column(String(16), unique=True, index=True, default="sandbox")
    connected_by_account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user_accounts.id"),
        index=True,
    )
    realm_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    company_name: Mapped[str] = mapped_column(String(255))
    legal_name: Mapped[str | None] = mapped_column(String(255))
    encrypted_access_token: Mapped[str | None] = mapped_column(Text)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refresh_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scopes_json: Mapped[list] = mapped_column(JSONType, default=list)
    status: Mapped[str] = mapped_column(String(32), default="connected")
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(500))


class QuickBooksOAuthState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quickbooks_oauth_states"

    state_digest: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    owner_account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user_accounts.id"),
        index=True,
    )
    environment: Mapped[str] = mapped_column(String(16), default="sandbox")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QuickBooksConfiguration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quickbooks_configurations"

    environment: Mapped[str] = mapped_column(String(16), unique=True, index=True, default="sandbox")
    configured_by_account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user_accounts.id"),
        index=True,
    )
    client_id: Mapped[str] = mapped_column(String(255))
    encrypted_client_secret: Mapped[str] = mapped_column(Text)
    encrypted_token_encryption_key: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
