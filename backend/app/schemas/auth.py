from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

UserRole = Literal["admin", "operations_manager", "estimator", "viewer"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=512)


class UserAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    display_name: str
    role: UserRole
    is_active: bool
    password_reset_required: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class UserAccountList(BaseModel):
    items: list[UserAccountRead]
    total: int


class UserAccountCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=255)
    role: UserRole = "viewer"
    password: str = Field(min_length=12, max_length=512)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Display name is required.")
        return normalized


class UserAccountUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("display_name")
    @classmethod
    def normalize_optional_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Display name cannot be blank.")
        return normalized


class PasswordResetRequest(BaseModel):
    password: str = Field(min_length=12, max_length=512)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=12, max_length=512)


class AuthStatus(BaseModel):
    authentication: str
    user: UserAccountRead


class RoleAccessRead(BaseModel):
    role: UserRole
    modules: dict[str, list[str]]
